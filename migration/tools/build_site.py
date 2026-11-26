#!/usr/bin/env python3
"""Экспорт содержательных материалов реестра в коллекции и страницы Jekyll (site/).

Вход:  migration/build/registry.json (см. extract.py), файлы site/images/.
Выход: содержательные файлы без каркаса оформления:
       site/_exhibitions/<slug>.html, site/_sections/<letter>.html,
       site/index.html, site/conclusion/index.html,
       а также отчёты migration/build/build_report.json и url_map.json.

Шаблоны, меню и стили живут непосредственно в site/ (_layouts/, _includes/,
_data/, assets/site.css) и этим скриптом не перезаписываются — оформление
и навигация отделены от содержания.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from datetime import date
from urllib.parse import quote, unquote

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
BUILD = os.path.join(ROOT, "build")
SITE = os.path.join(REPO, "site")
IMAGES = os.path.join(SITE, "images")
BASE_URL = os.environ.get("SITE_BASE_URL", "https://r2force.github.io/glossary")

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "j", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


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


def front_matter(**fields: object) -> str:
    lines = ["---"]
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, int):
            lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {json.dumps(str(value), ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines)


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
        if ":" in name:
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


def liquid_url(resolved: str) -> str:
    encoded = quote(resolved, safe="/:@?=&#%.+-_")
    return f"{{{{ '{encoded}' | relative_url }}}}"


def caption_for(item: dict | None, resolved: str) -> str:
    name = unquote(os.path.basename(resolved)).rsplit(".", 1)[0]
    name = name.replace("_", " ").strip()
    if item:
        return f"{item['title']}: {name}"
    return name


def rewrite_body(fragment: str, item: dict | None, media: Media,
                 usage: list[dict], page: str | None = None) -> str:
    """Очистка легаси-разметки, ссылки на изображения через relative_url, figure."""
    page = page or (item["path"] if item else "index.html")
    soup = BeautifulSoup(f"<div id='body'>{fragment}</div>", "html.parser")
    root = soup.find("div", id="body")
    strip_legacy_markup(root)

    for img in root.find_all("img"):
        src = (img.get("src") or "").strip()
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
        new_img["src"] = liquid_url(resolved)
        new_img["alt"] = alt
        new_img["loading"] = "lazy"
        full = media.resolve(full_src) if full_src else None
        if full and full != resolved:
            media.used.add(full)
            usage.append({"page": page, "image": full})
            link = soup.new_tag("a")
            link["href"] = liquid_url(full)
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
        if href.startswith(("mailto:", "#", "{{")):
            continue
        if anchor.find("img") or re.search(r"\.(jpe?g|png|gif)(\?|$)", href, re.I):
            continue
        if "glossary.ufacsdb.ru" in href or href.startswith("/index.php"):
            anchor.unwrap()
            continue
        if href.startswith("http"):
            anchor["rel"] = "nofollow noopener"
            continue
        anchor.unwrap()

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

    for tag in list(root.find_all(["p", "div", "li"])):
        if tag.decomposed or tag.parent is None:
            continue
        if not tag.get_text(strip=True) and not tag.find(["img", "figure", "a", "table"]):
            tag.decompose()

    blocks = []
    for child in root.children:
        chunk = str(child).strip()
        if chunk:
            chunk = re.sub(r"(<img\b[^>]*?)\s*/>", r"\1>", chunk)
            blocks.append(chunk)
    return "\n".join(blocks)


def page_url(path: str) -> str:
    if path.endswith("index.html"):
        directory = os.path.dirname(path)
        return f"{BASE_URL}/" + (directory + "/" if directory else "")
    return f"{BASE_URL}/{path}"


def main() -> int:
    with open(os.path.join(BUILD, "registry.json"), encoding="utf-8") as fh:
        registry = json.load(fh)

    media = Media()
    items = registry["items"]
    letters = registry["letters"]

    for folder in ("_exhibitions", "_sections"):
        target = os.path.join(SITE, folder)
        if os.path.isdir(target):
            shutil.rmtree(target)
        os.makedirs(target, exist_ok=True)

    written: list[str] = []
    image_usage: list[dict] = []

    def write(rel_path: str, content: str) -> None:
        full = os.path.join(SITE, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content.rstrip() + "\n")
        written.append(rel_path)

    featured_slugs = {i["slug"] for i in items if i["images"]}
    featured_slugs = {
        i["slug"] for i in [item for item in items if item["images"]][:6]
    }

    for order, item in enumerate(items, start=1):
        item["url"] = page_url(item["path"])
        body_html = rewrite_body(item["html"], item, media, image_usage)
        fm = front_matter(
            title=item["title"],
            letter=item["letter"],
            order=order,
            featured=True if item["slug"] in featured_slugs else None,
        )
        write(f"_exhibitions/{item['slug']}.html", f"{fm}\n{body_html}")

    for order, letter in enumerate(letters, start=1):
        title = letter["title"]
        slug = translit(title)
        fm = front_matter(
            title=f"Раздел «{title}»",
            letter=title,
            order=order,
        )
        write(f"_sections/{slug}.html", fm)

    intro_html = rewrite_body(registry["intro"]["html"], None, media, image_usage,
                              page="index.html")
    home_fm = front_matter(
        layout="home",
        description=(
            f"Глоссарий нетрадиционных форм книжных выставок: {len(items)} описаний, "
            "алфавитный указатель от А до Я, введение и заключение."
        ),
    )
    write("index.html", f"{home_fm}\n{intro_html}")

    conclusion_html = rewrite_body(registry["conclusion"]["html"], None, media,
                                   image_usage, page="conclusion/index.html")
    conclusion_fm = front_matter(
        layout="article",
        title="Заключение",
    )
    write("conclusion/index.html", f"{conclusion_fm}\n{conclusion_html}")

    report = {
        "generated": date.today().isoformat(),
        "content_files": len(written),
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
                    "source_file": f"site/_exhibitions/{i['slug']}.html",
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

    print("содержательных файлов:", len(written))
    print("выставок:", len(items))
    print("разделов:", len(letters))
    print("ссылок на изображения:", len(image_usage))
    print("изображений без файла:", len(media.missing))
    for miss in media.missing:
        print("  !", miss)
    return 0 if not media.missing else 1


if __name__ == "__main__":
    sys.exit(main())
