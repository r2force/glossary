#!/usr/bin/env python3
"""Сборка статического сайта глоссария в site/.

Вход:  migration/build/registry.json (см. extract.py), файлы site/images/.
Выход: site/index.html, site/introduction/, site/conclusion/,
       site/exhibitions/<slug>/, site/sections/<letter>/,
       site/assets/site.css, site/sitemap.xml, site/robots.txt, site/404.html.

Общая разметка (шапка, подвал, алфавит, навигация, карточки, стили) вынесена
в migration/templates/ и migration/tools/site_template.py: правится один раз,
попадает на все страницы. Ссылки на ресурсы — относительные, чтобы сайт работал
и по адресу https://r2force.github.io/glossary/, и локально. Повторный запуск
даёт те же файлы.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import sys
from datetime import date
from urllib.parse import quote, unquote

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from site_template import (
    BASE_URL,
    SITE_SUBTITLE,
    SITE_TITLE,
    article,
    breadcrumbs,
    cards,
    layout,
    letter_nav,
    pager,
    page_url,
    stylesheet,
    url_for,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
BUILD = os.path.join(ROOT, "build")
SITE = os.path.join(REPO, "site")
IMAGES = os.path.join(SITE, "images")

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "j", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


# ---------------------------------------------------------------- утилиты

def translit(value: str) -> str:
    out = []
    for char in value.lower():
        if char in TRANSLIT:
            out.append(TRANSLIT[char])
        elif char.isalnum():
            out.append(char)
        else:
            out.append(" ")
    return re.sub(r"[^a-z0-9]+", "-", "".join(out)).strip("-")


def plain(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    text = html.unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def short(text: str, limit: int = 200) -> str:
    text = plain(text)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,;:–-") + "…"


def meta_description(text: str) -> str:
    value = short(text, 180)
    return value if value else SITE_TITLE


# ---------------------------------------------------------------- изображения

class Media:
    """Сопоставление исходных адресов изображений с файлами site/images."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self.real: dict[str, bool] = {}
        for dirpath, _, names in os.walk(IMAGES):
            for name in names:
                if not name.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                    continue
                full = os.path.join(dirpath, name)
                key = "/" + os.path.relpath(full, SITE).replace(os.sep, "/")
                self.files[key] = full
                with open(full, "rb") as fh:
                    head = fh.read(40)
                self.real[key] = not head.startswith(b"version https://git-lfs")
        self.missing: list[dict] = []
        self.used: set[str] = set()

    def resolve(self, src: str) -> str | None:
        """Исходный адрес изображения -> путь внутри site/ (с учётом регистра)."""
        if src.startswith("file:"):
            return None
        path = unquote(src.split("?")[0].split("#")[0])
        if path.startswith("http"):
            path = "/" + path.split("/", 3)[-1]
        if not path.startswith("/"):
            path = "/images/stories/exhibition/" + path
        if path in self.files:
            return path
        lowered = {k.lower(): v for k, v in self.files.items()}
        if path.lower() in lowered:
            return path.lower()
        return None


# ---------------------------------------------------------------- сборка

def main() -> int:
    with open(os.path.join(BUILD, "registry.json"), encoding="utf-8") as fh:
        registry = json.load(fh)

    media = Media()
    items = registry["items"]
    letters = registry["letters"]

    # адреса берём из реестра (их же проверяет verify_site.py)
    for item in items:
        item["url"] = page_url(item["path"])

    by_letter: dict[str, list[dict]] = {}
    for item in items:
        by_letter.setdefault(item["letter"], []).append(item)

    letter_slug = {l["title"]: translit(l["title"]) for l in letters}
    letter_path = {
        l["title"]: f"sections/{letter_slug[l['title']]}/index.html" for l in letters
    }

    # чистка прежних выходных каталогов (не трогаем site/images)
    for folder in ("exhibitions", "sections", "assets", "contents",
                   "introduction", "conclusion"):
        target = os.path.join(SITE, folder)
        if os.path.isdir(target):
            shutil.rmtree(target)

    written: list[str] = []
    image_usage: list[dict] = []

    def write(path: str, content: str) -> None:
        full = os.path.join(SITE, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        written.append(path)

    # тексты введения и заключения готовятся один раз и переиспользуются
    intro_html = rewrite_body(registry["intro"]["html"], None, media, image_usage,
                              page="introduction/index.html")
    conclusion_html = rewrite_body(registry["conclusion"]["html"], None, media,
                                   image_usage, page="conclusion/index.html")
    home_crumb = ("Главная", "index.html")
    index_crumb = ("Указатель", "contents/index.html")

    # --- выставки
    for item in items:
        body_html = rewrite_body(item["html"], item, media, image_usage)
        siblings = by_letter[item["letter"]]
        position = siblings.index(item)
        prev_item = siblings[position - 1] if position > 0 else None
        next_item = siblings[position + 1] if position + 1 < len(siblings) else None
        body = "\n".join([
            breadcrumbs(item["path"], [
                home_crumb,
                index_crumb,
                (f'Раздел «{item["letter"]}»', letter_path[item["letter"]]),
            ]),
            article(item["title"], body_html,
                    pager(item["path"], prev_item, next_item)),
        ])
        write(
            item["path"],
            layout(
                item["path"],
                f'{item["title"]} — {SITE_TITLE}',
                meta_description(item["html"]),
                body,
                item["url"],
                extra_head=json_ld(item),
            ),
        )

    # --- разделы по буквам
    for letter in letters:
        title = letter["title"]
        path = letter_path[title]
        group = by_letter.get(title, [])
        entries = [
            (item["title"], item["path"], short(item["html"], 150))
            for item in group
        ]
        body = "\n".join([
            breadcrumbs(path, [home_crumb, index_crumb]),
            f'<h1>Раздел «{html.escape(title)}»</h1>',
            f'<p class="lead">Выставок в разделе: {len(group)}. '
            'Полные описания — на отдельных страницах.</p>',
            letter_nav(path, letter_path, current=title),
            cards(path, entries),
        ])
        write(
            path,
            layout(
                path,
                f'Раздел «{title}» — {SITE_TITLE}',
                f'Книжные выставки на букву «{title}»: {len(group)} описаний '
                f'из глоссария «Книга – Выставка – Читатель».',
                body,
                page_url(path),
            ),
        )

    # --- указатель
    def contents_link(target: str) -> str:
        return url_for("contents/index.html", target)

    toc = [
        '<h1>Алфавитный указатель</h1>',
        f'<p class="lead">Всего выставок: {len(items)}. Разделов: {len(letters)}.</p>',
        letter_nav("contents/index.html", letter_path),
    ]
    for letter in letters:
        title = letter["title"]
        group = sorted(by_letter.get(title, []), key=lambda i: i["title"])
        toc.append(
            f'<h2 id="letter-{letter_slug[title]}">'
            f'<a href="{contents_link(letter_path[title])}">{html.escape(title)}</a></h2>'
        )
        toc.append('<ul class="toc">')
        for item in group:
            toc.append(
                f'<li><a href="{contents_link(item["path"])}">'
                f'{html.escape(item["title"])}</a></li>'
            )
        toc.append("</ul>")
    write(
        "contents/index.html",
        layout(
            "contents/index.html",
            f"Алфавитный указатель — {SITE_TITLE}",
            f"Алфавитный указатель глоссария: {len(items)} нетрадиционных форм "
            "книжных выставок от А до Я.",
            "\n".join(toc),
            page_url("contents/index.html"),
        ),
    )

    # --- введение и заключение
    for path, key, heading, text in (
        ("introduction/index.html", "intro", "Введение", intro_html),
        ("conclusion/index.html", "conclusion", "Заключение", conclusion_html),
    ):
        body = "\n".join([
            breadcrumbs(path, [home_crumb]),
            article(heading, text),
        ])
        write(
            path,
            layout(
                path,
                f"{heading} — {SITE_TITLE}",
                meta_description(registry[key]["html"]),
                body,
                page_url(path),
            ),
        )

    # --- главная
    featured = [i for i in items if i["images"]][:6]
    entries = [
        (item["title"], item["path"], short(item["html"], 150))
        for item in featured
    ]
    home = "\n".join([
        f"<h1>{html.escape(SITE_TITLE)}</h1>",
        f'<p class="lead">{html.escape(SITE_SUBTITLE)}</p>',
        "<h2>Алфавитный указатель</h2>",
        letter_nav("index.html", letter_path),
        "<h2>Избранные выставки</h2>",
        cards("index.html", entries),
        "<h2>О глоссарии</h2>",
        intro_html,
    ])
    write(
        "index.html",
        layout(
            "index.html",
            f"{SITE_TITLE}: {SITE_SUBTITLE}",
            f"Глоссарий нетрадиционных форм книжных выставок: {len(items)} описаний, "
            "алфавитный указатель от А до Я, введение и заключение.",
            home,
            page_url("index.html"),
        ),
    )

    # --- стили
    write("assets/site.css", stylesheet())

    # --- 404
    not_found = "\n".join([
        "<h1>Страница не найдена</h1>",
        f'<p>Возможно, адрес изменился. Откройте '
        f'<a href="{url_for("404.html", "contents/index.html")}">алфавитный указатель</a> '
        f'или вернитесь на <a href="{url_for("404.html", "index.html")}">главную '
        'страницу</a>.</p>',
    ])
    write(
        "404.html",
        layout(
            "404.html",
            f"Страница не найдена — {SITE_TITLE}",
            "Запрошенная страница не найдена.",
            not_found,
            f"{BASE_URL}/404.html",
        ),
    )

    # --- SEO
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}/sitemap.xml\n")
    write("sitemap.xml", sitemap(items, letters, letter_path))

    # --- отчёты
    report = {
        "generated": date.today().isoformat(),
        "pages": len(written),
        "exhibitions": len(items),
        "letters": len(letters),
        "image_references": len(image_usage),
        "images_missing": media.missing,
        "images_non_lfs": sorted(k for k, real in media.real.items() if not real),
        "unused_images": sorted(set(media.files) - media.used),
    }
    with open(os.path.join(BUILD, "build_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(BUILD, "url_map.json"), "w", encoding="utf-8") as fh:
        json.dump(
            [
                {
                    "title": i["title"],
                    "letter": i["letter"],
                    "source_url": i["source_url"],
                    "source_id": i["source_id"],
                    "target_path": i["path"],
                    "url": i["url"],
                    "images": i["images"],
                }
                for i in items
            ],
            fh,
            ensure_ascii=False,
            indent=1,
        )

    print("страниц:", len(written))
    print("выставок:", len(items))
    print("ссылок на изображения:", len(image_usage))
    print("изображений без файла:", len(media.missing))
    for miss in media.missing:
        print("  !", miss)
    return 0 if not media.missing else 1


# ---------------------------------------------------------------- очистка разметки

# Устаревшие/служебные теги и атрибуты оформления, которые встречаются в
# материалах Joomla 1.5 и в HTML, выгруженном из Word.
DROP_TAGS = {
    "script", "style", "noscript", "iframe", "xml", "o:p", "frame", "frameset",
    "noframes", "applet", "basefont", "isindex",
}
UNWRAP_TAGS = {"u", "strike", "s", "tt", "big", "small", "font", "center",
               "span", "dir", "menu", "marquee", "blink", "acronym"}
DROP_ATTRS = {
    "style", "class", "lang", "dir", "align", "valign", "bgcolor", "border",
    "bordercolor", "cellpadding", "cellspacing", "width", "height", "color",
    "face", "size", "hspace", "vspace", "nowrap", "background", "clear",
    "language", "mce_src", "mce_href", "target",
}


def strip_legacy_markup(root: Tag) -> None:
    """Убрать легаси старого сайта: Word-стили, презентационные теги и атрибуты."""
    for comment in root.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    for tag in list(root.find_all(True)):
        if tag.decomposed:
            continue
        name = tag.name.lower()
        if name in DROP_TAGS:
            tag.decompose()
            continue
        if ":" in name:  # пространства имён Word/VML: оставляем только текст
            tag.unwrap()
            continue
        for attr in list(tag.attrs):
            low = attr.lower()
            if low in DROP_ATTRS or low.startswith("mso-") or low.startswith("on"):
                del tag.attrs[attr]
        if name == "b":
            tag.name = "strong"
        elif name == "i":
            tag.name = "em"
        elif name in UNWRAP_TAGS:
            tag.unwrap()

    for node in list(root.find_all(string=lambda t: isinstance(t, NavigableString)
                                   and not isinstance(t, Comment))):
        value = str(node)
        if "\xa0" in value or "\u200b" in value:
            node.replace_with(value.replace("\xa0", " ").replace("\u200b", ""))


def rewrite_body(fragment: str, item: dict | None, media: Media,
                 usage: list[dict], page: str | None = None) -> str:
    """Очистка легаси-разметки, относительные ссылки на изображения, figure,
    безопасные внешние ссылки."""
    page = page or (item["path"] if item else "index.html")
    soup = BeautifulSoup(f"<div id='body'>{fragment}</div>", "html.parser")
    root = soup.find("div", id="body")
    strip_legacy_markup(root)

    for img in root.find_all("img"):
        src = (img.get("src") or "").strip()
        # Ссылка вокруг иллюстрации ведёт на полный оригинал.
        full_src = ""
        anchor = img.parent
        if isinstance(anchor, Tag) and anchor.name == "a":
            full_src = (anchor.get("href") or "").strip()
        resolved = media.resolve(src)
        if resolved is None:
            media.missing.append(
                {"src": src, "page": page, "title": item["title"] if item else ""}
            )
            img.decompose()
            continue
        media.used.add(resolved)
        usage.append({"page": page, "image": resolved})
        alt = (img.get("alt") or "").strip() or caption_for(item, resolved)
        figure = soup.new_tag("figure")
        new_img = soup.new_tag("img")
        new_img["src"] = quote(url_for(page, resolved.lstrip("/")),
                              safe="/:@?=&#%.+-_")
        new_img["alt"] = alt
        new_img["loading"] = "lazy"
        full = media.resolve(full_src) if full_src else None
        if full and full != resolved:
            media.used.add(full)
            usage.append({"page": page, "image": full})
            link = soup.new_tag("a")
            link["href"] = quote(url_for(page, full.lstrip("/")),
                                 safe="/:@?=&#%.+-_")
            link.append(new_img)
            figure.append(link)
        else:
            figure.append(new_img)
        holder = anchor if isinstance(anchor, Tag) and anchor.name == "a" and \
            not anchor.get_text(strip=True) else img
        holder.replace_with(figure)
        if not holder.get_text(strip=True) and holder.name == "p" \
                and not holder.find(["a", "strong", "em"]):
            holder.unwrap()

    for anchor in root.find_all("a"):
        href = (anchor.get("href") or "").strip()
        if href.startswith(("javascript:", "file:", "data:")):
            anchor.unwrap()
            continue
        if href.startswith("mailto:") or href.startswith("#"):
            continue
        if anchor.find("img") or re.search(r"\.(jpe?g|png|gif)(\?|$)", href, re.I):
            # Ссылка на иллюстрацию остаётся ссылкой на полный оригинал.
            continue
        if "glossary.ufacsdb.ru" in href or href.startswith("/index.php"):
            # Внутренние адреса Joomla: переносим как простой текст,
            # чтобы не публиковать ссылки на старый сайт.
            anchor.unwrap()
            continue
        if href.startswith("http"):
            anchor["rel"] = "nofollow noopener"
            continue
        anchor.unwrap()

    # figure не может находиться внутри p: выносим её перед абзацем.
    for figure in root.find_all("figure"):
        node = figure.parent
        paragraph = None
        while node is not None and node is not root:
            if node.name == "p":
                paragraph = node
            node = node.parent
        if paragraph is not None:
            paragraph.insert_before(figure)
            if not paragraph.get_text(strip=True) and not paragraph.find(["img", "figure"]):
                paragraph.decompose()

    # пустые обёртки, оставшиеся после удаления оформления Word/Joomla
    for tag in list(root.find_all(["p", "div", "li"])):
        if tag.decomposed or tag.parent is None:
            continue
        if not tag.get_text(strip=True) and not tag.find(["img", "figure", "a", "table"]):
            tag.decompose()

    return root.decode_contents().strip()


def caption_for(item: dict | None, resolved: str) -> str:
    name = unquote(os.path.basename(resolved)).rsplit(".", 1)[0]
    name = name.replace("_", " ").strip()
    if item:
        return f"{item['title']}: {name}"
    return name


def json_ld(item: dict) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": item["title"],
        "inLanguage": "ru",
        "isPartOf": {"@type": "WebSite", "name": f"{SITE_TITLE}: {SITE_SUBTITLE}",
                     "url": f"{BASE_URL}/"},
        "mainEntityOfPage": item["url"],
    }
    return ('<script type="application/ld+json">'
            + json.dumps(data, ensure_ascii=False)
            + "</script>\n")


def sitemap(items, letters, letter_path) -> str:
    entries = [
        (f"{BASE_URL}/", "1.0"),
        (f"{BASE_URL}/introduction/", "0.9"),
        (f"{BASE_URL}/contents/", "0.9"),
        (f"{BASE_URL}/conclusion/", "0.8"),
    ]
    for letter in letters:
        entries.append((page_url(letter_path[letter["title"]]), "0.7"))
    for item in items:
        entries.append((item["url"], "0.8"))
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, priority in entries:
        parts.append(f"  <url><loc>{html.escape(loc)}</loc>"
                     f"<priority>{priority}</priority></url>")
    parts.append("</urlset>")
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    sys.exit(main())
