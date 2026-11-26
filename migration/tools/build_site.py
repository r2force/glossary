#!/usr/bin/env python3
"""Сборка статического сайта глоссария в site/.

Вход:  migration/build/registry.json (см. extract.py), файлы site/images/.
Выход: site/index.html, site/introduction/, site/conclusion/,
       site/exhibitions/<slug>/, site/sections/<letter>/,
       site/assets/site.css, site/sitemap.xml, site/robots.txt, site/404.html.

Ссылки на ресурсы — относительные, чтобы сайт работал и по адресу
https://r2force.github.io/glossary/, и локально. Повторный запуск даёт те же файлы.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import sys
import unicodedata
from datetime import date
from urllib.parse import quote, unquote

from bs4 import BeautifulSoup, Tag

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
BUILD = os.path.join(ROOT, "build")
SITE = os.path.join(REPO, "site")
IMAGES = os.path.join(SITE, "images")

SITE_TITLE = "«Книга – Выставка – Читатель»"
SITE_SUBTITLE = "глоссарий нетрадиционных форм книжных выставок"
ORG = "Центральная городская детская библиотека г. Уфы"
BASE_URL = os.environ.get("SITE_BASE_URL", "https://r2force.github.io/glossary")

LETTER_ORDER = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
SERVICE_IMAGES = {"images/logo/Book31.png"}
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


def slug_for(title: str, used: set[str]) -> str:
    base = translit(re.sub(r"^Выставка\s*[-–—]?\s*", "", title, flags=re.I)) or "vystavka"
    base = re.sub(r"-+", "-", base).strip("-")[:60] or "vystavka"
    slug = base
    index = 2
    while slug in used:
        slug = f"{base}-{index}"
        index += 1
    used.add(slug)
    return slug


def rel(from_path: str, to_path: str) -> str:
    """Относительный адрес между двумя файлами сайта (без обращения к ФС)."""
    import posixpath

    start = posixpath.dirname(from_path) or "."
    return posixpath.relpath("/" + to_path.lstrip("/"), "/" + start).lstrip("/")


def url_for(from_path: str, to_path: str) -> str:
    target = rel(from_path, to_path)
    if target.endswith("/") or target in (".", ""):
        return target
    return target


def page_url(path: str) -> str:
    """Канонический адрес страницы на GitHub Pages."""
    if path.endswith("index.html"):
        rel_dir = os.path.dirname(path)
        return f"{BASE_URL}/" + (rel_dir + "/" if rel_dir else "")
    return f"{BASE_URL}/{path}"


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


# ---------------------------------------------------------------- шаблоны

CSS = """
:root{--ink:#1d1b1a;--muted:#6b625c;--line:#ded6cf;--accent:#7d3d2e;--bg:#fbf8f5}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font:17px/1.65 "Iowan Old Style","Palatino Linotype",Georgia,serif}
a{color:var(--accent)}
a:hover{text-decoration:none}
.wrap{max-width:56rem;margin:0 auto;padding:0 1.25rem}
.skip{position:absolute;left:-999px}
.skip:focus{left:1rem;top:1rem;background:#fff;padding:.5rem 1rem;z-index:9}
header.site{border-bottom:1px solid var(--line);background:#fff}
header.site .wrap{display:flex;flex-wrap:wrap;gap:.5rem 1.5rem;
 align-items:baseline;padding-top:1rem;padding-bottom:1rem}
header.site .brand{font-weight:700;text-decoration:none;color:var(--ink);font-size:1.15rem}
header.site .brand span{display:block;font-size:.8rem;font-weight:400;color:var(--muted)}
nav.main{display:flex;flex-wrap:wrap;gap:.25rem .9rem;font-size:.92rem}
nav.main a{text-decoration:none}
nav.main a[aria-current]{text-decoration:underline;font-weight:700}
main{padding:2rem 0 3rem}
h1{font-size:2rem;line-height:1.2;margin:0 0 .5rem}
h2{font-size:1.35rem;margin:2rem 0 .75rem}
h3{font-size:1.1rem;margin:1.5rem 0 .5rem}
p{margin:0 0 1rem}
ul,ol{margin:0 0 1rem;padding-left:1.4rem}
li{margin:.25rem 0}
.lead{font-size:1.1rem;color:var(--muted)}
.crumbs{font-size:.85rem;color:var(--muted);margin-bottom:1rem}
.crumbs a{text-decoration:none}
article figure{margin:1.5rem 0;text-align:center}
article img{max-width:100%;height:auto;border:1px solid var(--line);
 background:#fff;padding:.35rem}
.letter-nav{display:flex;flex-wrap:wrap;gap:.35rem;margin:1.5rem 0;
 padding:0;list-style:none}
.letter-nav a{display:inline-block;min-width:2rem;text-align:center;
 padding:.2rem .45rem;border:1px solid var(--line);border-radius:.25rem;
 background:#fff;text-decoration:none}
.letter-nav a[aria-current]{background:var(--accent);color:#fff;border-color:var(--accent)}
.letter-nav .off{color:#b9b1aa;padding:.2rem .45rem}
.cards{display:grid;gap:1rem;grid-template-columns:repeat(auto-fill,minmax(16rem,1fr));
 padding:0;list-style:none;margin:1.5rem 0}
.cards li{border:1px solid var(--line);background:#fff;padding:1rem;border-radius:.35rem}
.cards h3{margin:0 0 .4rem;font-size:1.05rem}
.cards p{margin:0;font-size:.92rem;color:var(--muted)}
.toc{columns:2;column-gap:2rem;padding-left:1.2rem}
@media (max-width:44rem){.toc{columns:1}}
footer.site{border-top:1px solid var(--line);background:#fff;color:var(--muted);
 font-size:.88rem}
footer.site .wrap{padding:1.5rem 1.25rem}
ul:has(> li > figure){display:flex;flex-wrap:wrap;gap:.75rem;padding:0;list-style:none}
ul > li > figure{margin:0}
figure a{display:inline-block}
.note{border-left:3px solid var(--accent);padding:.25rem 0 .25rem 1rem;
 color:var(--muted);font-size:.92rem}
.pager{display:flex;justify-content:space-between;gap:1rem;margin-top:2.5rem;
 border-top:1px solid var(--line);padding-top:1rem;font-size:.95rem}
""".strip()


def header(current: str) -> str:
    here = current

    def link(path: str, label: str) -> str:
        attr = ' aria-current="page"' if path == current else ""
        return f'<a href="{url_for(here, path)}"{attr}>{label}</a>'

    return f"""<header class="site">
  <div class="wrap">
    <a class="brand" href="{url_for(here, "index.html")}">{SITE_TITLE}<span>{SITE_SUBTITLE}</span></a>
    <nav class="main" aria-label="Разделы сайта">
      {link("index.html", "Введение")}
      {link("contents/index.html", "Указатель")}
      {link("conclusion/index.html", "Заключение")}
    </nav>
  </div>
</header>"""


def footer(depth: str) -> str:
    return f"""<footer class="site">
  <div class="wrap">
    <p>{SITE_TITLE}: {SITE_SUBTITLE}. {ORG}.</p>
    <p>Материалы перенесены с сайта glossary.ufacsdb.ru с сохранением авторского текста.</p>
  </div>
</footer>"""


def depth_of(path: str) -> str:
    directory = os.path.dirname(path)
    return "../" * (len(directory.split("/")) if directory else 0)


def layout(path: str, title: str, description: str, body: str,
           canonical: str, extra_head: str = "") -> str:
    depth = depth_of(path)
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="canonical" href="{html.escape(canonical)}">
<meta property="og:type" content="article">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:url" content="{html.escape(canonical)}">
<meta property="og:locale" content="ru_RU">
<link rel="stylesheet" href="{url_for(path, "assets/site.css")}">
{extra_head}</head>
<body>
<a class="skip" href="#content">К содержанию</a>
{header(path)}
<main id="content">
  <div class="wrap">
{body}
  </div>
</main>
{footer(depth)}
</body>
</html>
"""


def letter_nav(current: str, depth: str, href_for) -> str:
    parts = ['<ul class="letter-nav" aria-label="Алфавитный указатель">']
    for letter in LETTER_ORDER:
        if letter in {"Ё", "Й", "Щ", "Ъ", "Ы", "Ь"}:
            continue
        if letter == current:
            parts.append(f'<li><a href="{href_for(letter)}" aria-current="page">{letter}</a></li>')
        elif href_for(letter):
            parts.append(f'<li><a href="{href_for(letter)}">{letter}</a></li>')
        else:
            parts.append(f'<li><span class="off">{letter}</span></li>')
    parts.append("</ul>")
    return "".join(parts)


def figure_block(img_path: str, alt: str, page_path: str) -> str:
    src = url_for(page_path, img_path.lstrip("/"))
    return (f'<figure><img src="{quote(src, safe="/:@?=&#%.+-_")}"'
            f' alt="{html.escape(alt)}" loading="lazy"></figure>')


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
    letter_path = {l["title"]: f"sections/{letter_slug[l['title']]}/index.html" for l in letters}

    # чистка прежних выходных каталогов (не трогаем site/images)
    for folder in ("exhibitions", "sections", "assets", "contents",
                   "introduction", "conclusion"):
        target = os.path.join(SITE, folder)
        if os.path.isdir(target):
            shutil.rmtree(target)

    def href(letter: str) -> str | None:
        return letter_path.get(letter)

    written: list[str] = []
    image_usage: list[dict] = []

    def write(path: str, content: str) -> None:
        full = os.path.join(SITE, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        written.append(path)

    # --- выставки
    for index, item in enumerate(items):
        body_html = rewrite_body(item["html"], item, media, image_usage)
        siblings = by_letter[item["letter"]]
        position = siblings.index(item)
        prev_item = siblings[position - 1] if position > 0 else None
        next_item = siblings[position + 1] if position + 1 < len(siblings) else None
        pager = ['<nav class="pager" aria-label="Соседние выставки">']
        pager.append(
            f'<span>← <a href="{url_for(item["path"], prev_item["path"])}">{html.escape(prev_item["title"])}</a></span>'
            if prev_item else "<span></span>"
        )
        pager.append(
            f'<span><a href="{url_for(item["path"], next_item["path"])}">{html.escape(next_item["title"])}</a> →</span>'
            if next_item else "<span></span>"
        )
        pager.append("</nav>")
        description = meta_description(item["html"])
        body = f"""    <nav class="crumbs" aria-label="Хлебные крошки">
      <a href="{url_for(item["path"], "index.html")}">Введение</a> ·
      <a href="{url_for(item["path"], "contents/index.html")}">Указатель</a> ·
      <a href="{url_for(item["path"], letter_path[item["letter"]])}">Раздел «{item["letter"]}»</a>
    </nav>
    <article>
      <h1>{html.escape(item["title"])}</h1>
{body_html}
{''.join(pager)}
    </article>"""
        write(
            item["path"],
            layout(
                item["path"],
                f'{item["title"]} — {SITE_TITLE}',
                description,
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
        cards = ['<ul class="cards">']
        for item in group:
            preview = short(item["html"], 150)
            cards.append(
                f'<li><h3><a href="{url_for(path, item["path"])}">{html.escape(item["title"])}</a></h3>'
                + (f"<p>{html.escape(preview)}</p>" if preview else "")
                + "</li>"
            )
        cards.append("</ul>")
        body = f"""    <nav class="crumbs" aria-label="Хлебные крошки">
      <a href="{url_for(path, "index.html")}">Введение</a> ·
      <a href="{url_for(path, "contents/index.html")}">Указатель</a>
    </nav>
    <h1>Раздел «{html.escape(title)}»</h1>
    <p class="lead">Выставок в разделе: {len(group)}. Полные описания — на отдельных страницах.</p>
{letter_nav(title, path, lambda letter: url_for(path, letter_path[letter]) if letter in letter_path else None)}
{''.join(cards)}"""
        write(
            path,
            layout(
                path,
                f'Раздел «{title}» — {SITE_TITLE}',
                f'Книжные выставки на букву «{title}»: {len(group)} описаний из глоссария «Книга – Выставка – Читатель».',
                body,
                page_url(path),
            ),
        )

    # --- указатель
    toc = ['<h1>Алфавитный указатель</h1>',
           f'<p class="lead">Всего выставок: {len(items)}. Разделов: {len(letters)}.</p>',
           letter_nav("", "contents/index.html",
                      lambda letter: url_for("contents/index.html", letter_path[letter])
                      if letter in letter_path else None)]
    for letter in letters:
        title = letter["title"]
        group = sorted(by_letter.get(title, []), key=lambda i: i["title"])
        toc.append(f'<h2 id="letter-{letter_slug[title]}">'
                   f'<a href="{url_for("contents/index.html", letter_path[title])}">{html.escape(title)}</a></h2>')
        toc.append('<ul class="toc">')
        for item in group:
            toc.append(
                f'<li><a href="{url_for("contents/index.html", item["path"])}">{html.escape(item["title"])}</a></li>'
            )
        toc.append("</ul>")
    write(
        "contents/index.html",
        layout(
            "contents/index.html",
            f"Алфавитный указатель — {SITE_TITLE}",
            f"Алфавитный указатель глоссария: {len(items)} нетрадиционных форм книжных выставок от А до Я.",
            "\n    ".join(toc),
            page_url("contents/index.html"),
        ),
    )

    # --- введение и заключение
    write(
        "introduction/index.html",
        layout(
            "introduction/index.html",
            f"Введение — {SITE_TITLE}",
            meta_description(registry["intro"]["html"]),
            f"""    <nav class="crumbs"><a href="{url_for("introduction/index.html", "index.html")}">Главная</a></nav>
    <article>
      <h1>Введение</h1>
{rewrite_body(registry["intro"]["html"], None, media, image_usage)}
    </article>""",
            page_url("introduction/index.html"),
        ),
    )
    write(
        "conclusion/index.html",
        layout(
            "conclusion/index.html",
            f"Заключение — {SITE_TITLE}",
            meta_description(registry["conclusion"]["html"]),
            f"""    <nav class="crumbs"><a href="{url_for("conclusion/index.html", "index.html")}">Главная</a></nav>
    <article>
      <h1>Заключение</h1>
{rewrite_body(registry["conclusion"]["html"], None, media, image_usage)}
    </article>""",
            page_url("conclusion/index.html"),
        ),
    )

    # --- главная
    featured = [i for i in items if i["images"]][:6]
    cards = ['<ul class="cards">']
    for item in featured:
        cards.append(
            f'<li><h3><a href="{url_for("index.html", item["path"])}">{html.escape(item["title"])}</a></h3>'
            f'<p>{html.escape(short(item["html"], 150))}</p></li>'
        )
    cards.append("</ul>")
    letter_links = letter_nav("", "index.html",
                              lambda letter: url_for("index.html", letter_path[letter])
                              if letter in letter_path else None)
    home = f"""    <h1>{SITE_TITLE}</h1>
    <p class="lead">{SITE_SUBTITLE}</p>
    <p><a href="{url_for("index.html", "introduction/index.html")}">Введение</a> ·
    <a href="{url_for("index.html", "contents/index.html")}">Алфавитный указатель</a> ·
    <a href="{url_for("index.html", "conclusion/index.html")}">Заключение</a></p>
    <h2>Алфавитный указатель</h2>
{letter_links}
    <h2>Избранные выставки</h2>
{''.join(cards)}
    <h2>О глоссарии</h2>
{rewrite_body(registry["intro"]["html"], None, media, image_usage)}"""
    write(
        "index.html",
        layout(
            "index.html",
            f"{SITE_TITLE}: {SITE_SUBTITLE}",
            f"Глоссарий нетрадиционных форм книжных выставок: {len(items)} описаний, алфавитный указатель от А до Я, введение и заключение.",
            home,
            page_url("index.html"),
        ),
    )

    # --- стили
    write("assets/site.css", CSS + "\n")

    # --- 404
    write(
        "404.html",
        layout(
            "404.html",
            f"Страница не найдена — {SITE_TITLE}",
            "Запрошенная страница не найдена.",
            f"""    <h1>Страница не найдена</h1>
    <p>Возможно, адрес изменился. Откройте <a href="{url_for("404.html", "contents/index.html")}">алфавитный указатель</a>
    или вернитесь на <a href="{url_for("404.html", "index.html")}">главную страницу</a>.</p>""",
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
        "unused_images": sorted(set(media.files) - media.used - {"/" + p for p in SERVICE_IMAGES}),
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


def rewrite_body(fragment: str, item: dict | None, media: Media,
                 usage: list[dict]) -> str:
    """Относительные ссылки на изображения, figure, безопасные внешние ссылки."""
    page = item["path"] if item else "index.html"
    soup = BeautifulSoup(f"<div id='body'>{fragment}</div>", "html.parser")
    root = soup.find("div", id="body")

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
                and not holder.find(["a", "strong", "em", "b", "i"]):
            holder.unwrap()


    for anchor in root.find_all("a"):
        href = (anchor.get("href") or "").strip()
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
