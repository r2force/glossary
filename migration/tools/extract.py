#!/usr/bin/env python3
"""Разбор собранных страниц glossary.ufacsdb.ru в реестр материалов.

Вход:  migration/source/pages/*.html + manifest.json
Выход: migration/build/registry.json — введение, заключение, все выставки
       migration/REPORT_INVENTORY.md — отчёт инвентаризации

Структура источника (Joomla 1.5):
  * /                       — ВВЕДЕНИЕ;
  * view=article&id=284     — ЗАКЛЮЧЕНИЕ;
  * view=article&id=320…341 — буквенные страницы А…Я с раскрывающимися карточками;
  * view=article&id=<прочие>— отдельные статьи выставок (тот же текст, что в карточках).

Каждая выставка получает запись с заголовком, семантическим HTML, списком
изображений и ссылкой на букву указателя.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from urllib.parse import parse_qs, unquote, urlsplit

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "source")
OUT = os.path.join(ROOT, "build")
BASE_HOST = "glossary.ufacsdb.ru"

INTRO_ID = "285"
CONCLUSION_ID = "284"
SERVICE_IDS = {"287"}  # «Выход» — служебная страница закрытия окна

TRANSPARENT = {"div", "span", "font", "center", "tbody", "thead", "section",
               "article", "body", "html", "blockquote"}
INLINE_WRAP = {"strong", "b", "em", "i", "u", "sup", "sub", "big", "small"}


def load_manifest():
    with open(os.path.join(SRC, "manifest.json"), encoding="utf-8") as fh:
        return json.load(fh)


def page_html(entry):
    with open(os.path.join(SRC, "pages", entry["file"]), encoding="utf-8") as fh:
        return fh.read()


def clean_text(value: str) -> str:
    value = value.replace("\xa0", " ").replace("\u200b", "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def strip_noise(root: Tag) -> None:
    for tag in root.find_all(["script", "style", "noscript", "iframe", "o:p", "xml"]):
        tag.decompose()
    for comment in root.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()


def render_img(tag: Tag) -> str:
    src = (tag.get("src") or tag.get("mce_src") or "").strip()
    if not src or src.startswith("data:"):
        return ""
    alt = clean_text(tag.get("alt") or "")
    return f'<img src="{escape(src)}" alt="{escape(alt)}">'


def render_link(tag: Tag) -> str:
    href = (tag.get("href") or "").strip()
    inner = serialize(tag, inline=True).strip()
    text = clean_text(tag.get_text(" "))
    if not inner and not text:
        return ""
    if not href:
        return inner
    return f'<a href="{escape(href)}">{inner or escape(text)}</a>'


def inline_text(value: str) -> str:
    """Текст внутри строкового контекста: одиночные пробелы, без обрезки."""
    value = value.replace("\xa0", " ").replace("\u200b", "")
    value = re.sub(r"\s+", " ", value)
    return value


def serialize(node: Tag, inline: bool = False) -> str:
    """Семантический HTML: p, списки, таблицы, ссылки, изображения."""
    out: list[str] = []
    for child in node.children:
        if isinstance(child, Comment):
            continue
        if isinstance(child, NavigableString):
            if inline:
                text = inline_text(str(child))
                if text.strip():
                    out.append(escape(text))
            else:
                text = clean_text(str(child))
                if text:
                    out.append(f"<p>{escape(text)}</p>")
            continue
        if not isinstance(child, Tag):
            continue
        name = child.name.lower()
        if name in {"script", "style", "noscript", "iframe", "o:p", "xml"}:
            continue
        if name in TRANSPARENT:
            out.append(serialize(child, inline))
        elif name in {"p", "address", "pre"}:
            inner = serialize(child, inline=True)
            text = clean_text(child.get_text(" "))
            if not text and "<img" not in inner:
                continue
            out.append(f"<p>{inner}</p>")
        elif name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            inner = serialize(child, inline=True)
            if not clean_text(child.get_text(" ")) and "<img" not in inner:
                continue
            inner = re.sub(r"^<p>|</p>$", "", inner.strip())
            out.append(f"<{name}>{inner}</{name}>")
        elif name in {"ul", "ol", "menu", "dir"}:
            tag = "ul" if name in {"menu", "dir"} else name
            out.append(f"<{tag}>{serialize(child, inline=True)}</{tag}>")
        elif name == "li":
            out.append(f"<li>{serialize(child, inline=True)}</li>")
        elif name == "table":
            out.append(f"<table>{serialize(child, inline=True)}</table>")
        elif name in {"tr", "td", "th"}:
            out.append(f"<{name}>{serialize(child, inline=True)}</{name}>")
        elif name == "img":
            out.append(render_img(child))
        elif name == "a":
            out.append(render_link(child))
        elif name == "br":
            continue
        elif name in INLINE_WRAP:
            inner = serialize(child, inline=True)
            if not inner.strip():
                continue
            if re.search(r"<(p|li|table|ul|ol)[ >]", inner):
                out.append(inner)
            else:
                out.append(f"<{name}>{inner}</{name}>")
        else:
            out.append(serialize(child, inline))
    return "".join(out)


def body_of(article: Tag) -> Tag:
    """Копия статьи без заголовка, кнопок печати и служебных скриптов."""
    clone = BeautifulSoup(str(article), "lxml").select_one("div.article")
    for part in clone.select("div.icons, div.headline"):
        part.decompose()
    strip_noise(clone)
    return clone


def images_in(node: Tag) -> list[str]:
    result = []
    for img in node.find_all("img"):
        src = (img.get("src") or "").strip()
        if not src or src.startswith("data:") or src.startswith("file:"):
            continue
        result.append(src)
    return result


def drop_service_lines(node: Tag) -> None:
    """Убираем подпись Joomla «Автор: … | дата» и сломанные локальные ссылки."""
    for img in node.find_all("img"):
        src = (img.get("src") or "").strip()
        if src.startswith("file:"):
            img.decompose()
    for tag in node.find_all(["p", "div", "span"]):
        if re.match(r"^\s*Автор:\s*Administrator\s*\|", tag.get_text(" ") or ""):
            tag.decompose()


def accordion_pairs(article: Tag) -> list[tuple[str, Tag]]:
    """Карточки буквенной страницы: (заголовок, тело)."""
    pairs = []
    for inner in article.select("div.sp-accordion-inner"):
        toggler = inner.find_previous_sibling("div", class_="toggler")
        title = clean_text(toggler.get_text(" ")) if toggler else ""
        pairs.append((title, inner))
    return pairs


def fix_cloaked_email(html: str) -> str:
    """Joomla прячет адрес скриптом; восстанавливаем известный адрес."""
    if "metodcsdb" in html and "mailto:" in html:
        html = re.sub(
            r"<a href=\"mailto:.*?</a>",
            '<a href="mailto:metodcsdb@gmail.com">metodcsdb@gmail.com</a>',
            html,
            flags=re.S,
        )
        html = re.sub(r"Этот e-mail адрес защищен.*?Javascript", "", html, flags=re.S)
    return html


def from_registry() -> int:
    """Использовать сохранённый реестр как источник сборки (для CI).

    Реестр в migration/build/registry.json уже содержит нормализованные тексты;
    при наличии сырья он пересобирается заново, иначе используется как есть.
    """
    path = os.path.join(OUT, "registry.json")
    if not os.path.exists(path):
        print("реестр отсутствует — извлекаю из сырья", file=sys.stderr)
        return main()
    with open(path, encoding="utf-8") as fh:
        registry = json.load(fh)
    print(
        "реестр готов:",
        len(registry["items"]), "выставок,",
        len(registry["letters"]), "букв",
    )
    return 0


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    manifest = load_manifest()
    ok = [p for p in manifest if p.get("status") == "ok"]

    by_id: dict[str, list[dict]] = defaultdict(list)
    root_entries = []
    for entry in ok:
        url = entry["url"]
        query = parse_qs(urlsplit(url).query)
        if "format" in query and query["format"][0] == "pdf":
            continue
        if entry.get("title", "").startswith("%PDF"):
            continue
        if query.get("view") == ["article"] and "id" in query:
            by_id[query["id"][0].split(":")[0]].append(entry)
        elif url.rstrip("/") == f"https://{BASE_HOST}":
            root_entries.append(entry)

    letters: dict[str, dict] = {}
    exhibitions: dict[str, dict] = {}
    problems: list[dict] = []

    for aid, entries in by_id.items():
        best = max(entries, key=lambda e: e["text_length"])
        soup = BeautifulSoup(page_html(best), "lxml")
        article = soup.select_one("div.article")
        if article is None:
            problems.append({"source_id": aid, "issue": "нет div.article"})
            continue
        heading = article.select_one("h1.title")
        title = clean_text(heading.get_text(" ")) if heading else ""
        cards = accordion_pairs(article)

        if cards:
            letters[title] = {
                "kind": "letter",
                "source_id": aid,
                "source_url": best["url"],
                "title": title,
                "cards": [
                    {
                        "title": card_title,
                        "html": fix_cloaked_email(
                            serialize(BeautifulSoup(str(inner), "lxml").select_one(
                                "div.sp-accordion-inner"
                            )).strip()
                        ),
                        "images": images_in(inner),
                    }
                    for card_title, inner in cards
                ],
            }
            continue

        if aid in SERVICE_IDS:
            continue
        if aid in {INTRO_ID, CONCLUSION_ID}:
            continue

        body = body_of(article)
        drop_service_lines(body)
        exhibitions[aid] = {
            "kind": "article",
            "source_id": aid,
            "source_url": best["url"],
            "title": title,
            "html": fix_cloaked_email(serialize(body).strip()),
            "images": images_in(body),
        }

    # Буквы в порядке алфавита.
    letter_order = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
    ordered_letters = sorted(
        letters.values(),
        key=lambda l: (letter_order.index(l["title"]) if l["title"] in letter_order else 99, l["title"]),
    )

    # Экспонаты: источник текста — буквенная карточка (порядок указателя),
    # отдельная статья используется, если карточки нет.
    card_titles: dict[str, dict] = {}
    for letter in ordered_letters:
        for card in letter["cards"]:
            key = normalize_title(card["title"])
            card["letter"] = letter["title"]
            if key in card_titles:
                problems.append(
                    {"issue": "дубль карточки", "title": card["title"],
                     "letters": [card_titles[key]["letter"], letter["title"]]}
                )
                continue
            card_titles[key] = card

    article_by_title = {normalize_title(e["title"]): e for e in exhibitions.values()}

    items = []
    used_articles = set()
    for letter in ordered_letters:
        for card in letter["cards"]:
            key = normalize_title(card["title"])
            match = article_by_title.get(key)
            if match:
                used_articles.add(match["source_id"])
                source_id = match["source_id"]
                source_url = match["source_url"]
                html = match["html"] or card["html"]
                images = match["images"] or card["images"]
                matched = True
            else:
                source_id = ""
                source_url = letter["source_url"]
                html = card["html"]
                images = card["images"]
                matched = False
                problems.append(
                    {"issue": "нет отдельной статьи", "title": card["title"],
                     "letter": letter["title"]}
                )
            items.append(
                {
                    "kind": "exhibition",
                    "title": card["title"],
                    "letter": letter["title"],
                    "source_id": source_id,
                    "source_url": source_url,
                    "letter_source_url": letter["source_url"],
                    "html": html,
                    "images": images,
                    "has_own_page": matched,
                    "slug": "",
                }
            )

    for aid, record in exhibitions.items():
        if aid in used_articles:
            continue
        problems.append(
            {"issue": "статья вне указателя", "source_id": aid, "title": record["title"]}
        )
        items.append(
            {
                "kind": "exhibition",
                "title": record["title"],
                "letter": "",
                "source_id": aid,
                "source_url": record["source_url"],
                "letter_source_url": "",
                "html": record["html"],
                "images": record["images"],
                "has_own_page": True,
                "slug": "",
            }
        )

    # Введение и заключение.
    root_entry = max(root_entries, key=lambda e: e["text_length"]) if root_entries else None
    intro = None
    if root_entry:
        soup = BeautifulSoup(page_html(root_entry), "lxml")
        body = body_of(soup.select_one("div.article"))
        drop_service_lines(body)
        intro = {
            "kind": "intro",
            "source_id": INTRO_ID,
            "source_url": root_entry["url"],
            "title": "Введение",
            "html": fix_cloaked_email(serialize(body).strip()),
            "images": images_in(body),
        }

    conclusion = None
    if CONCLUSION_ID in by_id:
        entry = max(by_id[CONCLUSION_ID], key=lambda e: e["text_length"])
        soup = BeautifulSoup(page_html(entry), "lxml")
        body = body_of(soup.select_one("div.article"))
        drop_service_lines(body)
        conclusion = {
            "kind": "conclusion",
            "source_id": CONCLUSION_ID,
            "source_url": entry["url"],
            "title": "Заключение",
            "html": fix_cloaked_email(serialize(body).strip()),
            "images": images_in(body),
        }

    # Устойчивые адреса страниц: slug из заголовка, порядок — от указателя.
    used: set[str] = set()
    for item in items:
        base = translit(re.sub(r"^Выставка\s*[-–—]?\s*", "", item["title"], flags=re.I))
        base = re.sub(r"-+", "-", base).strip("-")[:60] or "vystavka"
        slug, index = base, 2
        while slug in used:
            slug = f"{base}-{index}"
            index += 1
        used.add(slug)
        item["slug"] = slug
        item["path"] = f"exhibitions/{slug}/index.html"

    registry = {
        "source_host": BASE_HOST,
        "letters": ordered_letters,
        "intro": intro,
        "conclusion": conclusion,
        "items": items,
        "problems": problems,
    }
    with open(os.path.join(OUT, "registry.json"), "w", encoding="utf-8") as fh:
        json.dump(registry, fh, ensure_ascii=False, indent=1)

    print("букв:", len(ordered_letters))
    print("выставок:", len(items))
    print("из них с отдельной страницей-статьёй:", sum(1 for i in items if i["has_own_page"]))
    print("введение:", bool(intro), "заключение:", bool(conclusion))
    print("проблем:", len(problems))
    for problem in problems[:20]:
        print("  !", problem)
    return 0


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


def normalize_title(title: str) -> str:
    value = title.lower().replace("ё", "е")
    value = re.sub(r"[^a-zа-я0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


if __name__ == "__main__":
    sys.exit(from_registry() if "--from-registry" in sys.argv else main())
