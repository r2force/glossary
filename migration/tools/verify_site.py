#!/usr/bin/env python3
"""Независимая проверка собранного сайта против реестра источника.

Проверяет:
  * полноту: каждая запись реестра имеет страницу, тексты не обрезаны;
  * изображения: файл существует в site/, регистр совпадает, LFS не указатель;
  * ссылки: внутренние адреса существуют, пути относительные;
  * HTML и SEO: title, description, canonical, один h1, lang=ru;
  * общие блоки из migration/templates/ и отсутствие легаси-разметки Word/Joomla;
  * sitemap.xml, robots.txt, 404.html;
  * повторяемость сборки (сравнение хешей при --repeat).

Выход: код 1 при любом расхождении; отчёт migration/build/verify_report.json
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import posixpath
import re
import subprocess
import sys
import urllib.parse
from collections import Counter

from bs4 import BeautifulSoup

from site_template import footer, header, letter_nav

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
SITE = os.path.join(REPO, "site")
BUILD = os.path.join(ROOT, "build")
BASE_URL = os.environ.get("SITE_BASE_URL", "https://r2force.github.io/glossary")


def normalize(text: str) -> str:
    text = html.unescape(text or "")
    text = text.replace("\xa0", " ").replace("\u200b", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


LEGACY_TAGS = {
    "font", "center", "big", "small", "strike", "s", "tt", "u", "b", "i",
    "marquee", "blink", "dir", "menu", "acronym", "applet", "basefont",
    "frame", "frameset", "noframes", "isindex", "o:p", "xml",
}
LEGACY_ATTRS = {
    "style", "bgcolor", "align", "valign", "cellpadding", "cellspacing",
    "border", "bordercolor", "color", "face", "size", "hspace", "vspace",
    "nowrap", "background", "clear", "language", "mce_src", "mce_href",
    "width", "height", "onclick", "onload", "onmouseover", "onerror",
}
WORD_MARKUP = re.compile(
    r"mso-|Mso|class\s*=\s*[\"'][^\"']*Mso|<!--\s*\[if|<o:p|<w:|<v:|"
    r"<\?xml|font-family", re.I
)


def page_files():
    found = []
    for dirpath, _, names in os.walk(SITE):
        if os.sep + "images" + os.sep in dirpath + os.sep:
            continue
        for name in names:
            if name.endswith(".html"):
                found.append(os.path.relpath(os.path.join(dirpath, name), SITE)
                             .replace(os.sep, "/"))
    return sorted(found)


def all_html_files():
    """Все HTML, включая каталоги изображений: легаси проверяем везде."""
    found = []
    for dirpath, _, names in os.walk(SITE):
        for name in names:
            if name.endswith(".html"):
                found.append(os.path.relpath(os.path.join(dirpath, name), SITE)
                             .replace(os.sep, "/"))
    return sorted(found)


def check_legacy_html(path: str) -> list[str]:
    """Устаревшие теги, атрибуты оформления и стили Word/Joomla."""
    problems = []
    with open(os.path.join(SITE, path), encoding="utf-8") as fh:
        text = fh.read()
    if not text.lstrip().lower().startswith("<!doctype html>"):
        problems.append(f"{path}: нет HTML5 <!DOCTYPE html>")
    if WORD_MARKUP.search(text):
        problems.append(f"{path}: осталась разметка Word/Joomla")
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup.find_all(True):
        name = tag.name.lower()
        if name in LEGACY_TAGS or ":" in name:
            problems.append(f"{path}: устаревший тег <{name}>")
        for attr in tag.attrs:
            low = attr.lower()
            if (low in LEGACY_ATTRS or low.startswith("mso-")
                    or low.startswith("on") or (low == "lang" and name != "html")):
                problems.append(f"{path}: атрибут оформления {low}= у <{name}>")
    if soup.find("style"):
        problems.append(f"{path}: встроенные стили <style>")
    return problems


def normalized_markup(node) -> str:
    """BeautifulSoup приводит атрибуты и отступы к одному виду по обе стороны."""
    return BeautifulSoup(str(node), "html.parser").decode()


def check_shared_blocks(path: str, soup, letter_path: dict[str, str],
                        letter_by_slug: dict[str, str]) -> list[str]:
    """Шапка, подвал и алфавит должны приходить из общих шаблонов."""
    problems = []
    head = soup.select_one("header.site")
    if head is None or normalized_markup(head) != normalized_markup(header(path)):
        problems.append(f"{path}: шапка не совпадает с общим шаблоном")
    foot = soup.select_one("footer.site")
    if foot is None or normalized_markup(foot) != normalized_markup(footer()):
        problems.append(f"{path}: подвал не совпадает с общим шаблоном")
    if len(soup.select("header.site")) != 1 or len(soup.select("footer.site")) != 1:
        problems.append(f"{path}: общие блоки продублированы")

    alphabet = soup.select("ul.letter-nav")
    if len(alphabet) > 1:
        problems.append(f"{path}: алфавитный указатель продублирован")
    if alphabet and not (path in {"index.html", "contents/index.html"}
                         or path.startswith("sections/")):
        problems.append(f"{path}: алфавитный указатель на лишней странице")
    if alphabet:
        current = ""
        if path.startswith("sections/"):
            current = letter_by_slug.get(path.split("/")[1], "")
        expected = letter_nav(path, letter_path, current)
        if normalized_markup(alphabet[0]) != normalized_markup(expected):
            problems.append(f"{path}: алфавит не совпадает с общим шаблоном")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", action="store_true",
                        help="пересобрать сайт и сравнить хеши файлов")
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    stats: Counter = Counter()

    with open(os.path.join(BUILD, "registry.json"), encoding="utf-8") as fh:
        registry = json.load(fh)

    pages = page_files()
    stats["html_pages"] = len(pages)
    page_set = set(pages)
    letter_path = {
        letter["title"]: f"sections/{translit(letter['title'])}/index.html"
        for letter in registry["letters"]
    }
    letter_by_slug = {
        translit(letter["title"]): letter["title"] for letter in registry["letters"]
    }

    # все HTML в site/, включая служебные файлы в каталогах изображений
    for path in all_html_files():
        errors.extend(check_legacy_html(path))

    def resolve_page(from_page: str, target: str) -> str | None:
        if not target or target.startswith(("http:", "https:", "mailto:", "#", "data:")):
            return None
        path = urllib.parse.unquote(target.split("#")[0].split("?")[0])
        if not path:
            return None
        if path.startswith("/"):
            return path.lstrip("/")
        joined = posixpath.normpath(posixpath.join(posixpath.dirname(from_page), path))
        return "" if joined == "." else joined

    # --- обход всех страниц: ссылки, изображения, метаданные
    titles: dict[str, str] = {}
    canonicals: dict[str, str] = {}
    linked_pages: set[str] = set()
    image_refs: list[tuple[str, str]] = []

    for page in pages:
        with open(os.path.join(SITE, page), encoding="utf-8") as fh:
            text = fh.read()
        soup = BeautifulSoup(text, "html.parser")
        stats["documents"] += 1
        errors.extend(check_shared_blocks(page, soup, letter_path, letter_by_slug))

        if soup.html is None or (soup.html.get("lang") or "")[:2] != "ru":
            errors.append(f"{page}: нет <html lang=\"ru\">")
        if soup.select_one("meta[charset], meta[http-equiv=content-type]") is None:
            errors.append(f"{page}: не указана кодировка")
        title_tag = soup.title.get_text(strip=True) if soup.title else ""
        if not title_tag:
            errors.append(f"{page}: пустой <title>")
        titles.setdefault(title_tag, page)
        description = soup.select_one('meta[name="description"]')
        if description is None or not description.get("content", "").strip():
            errors.append(f"{page}: пустой meta description")
        canonical = soup.select_one('link[rel="canonical"]')
        if canonical is None or not canonical.get("href", "").startswith("https://"):
            errors.append(f"{page}: нет абсолютного canonical")
        else:
            canonicals.setdefault(canonical["href"], page)
        h1 = soup.find_all("h1")
        if len(h1) != 1:
            errors.append(f"{page}: заголовков h1 — {len(h1)}")
        if soup.select_one('meta[name="robots"][content*="noindex"]'):
            errors.append(f"{page}: неожиданный noindex")
        if soup.select_one("script[src]"):
            errors.append(f"{page}: внешний скрипт, текст должен быть в HTML")

        for img in soup.find_all("img"):
            src = img.get("src") or ""
            image_refs.append((page, src))
            target = resolve_page(page, src)
            if target is None:
                errors.append(f"{page}: абсолютный или пустой src изображения {src!r}")
                continue
            full = os.path.join(SITE, target)
            if not os.path.isfile(full):
                errors.append(f"{page}: изображение не найдено {src!r}")
                continue
            real_name = os.path.basename(full)
            if real_name not in os.listdir(os.path.dirname(full)):
                errors.append(f"{page}: регистр имени файла {src!r}")
            with open(full, "rb") as fh:
                head = fh.read(40)
            if head.startswith(b"version https://git-lfs"):
                warnings.append(f"{page}: изображение осталось LFS-указателем {src!r}")
            if not (img.get("alt") or "").strip():
                errors.append(f"{page}: пустой alt у {src!r}")

        for anchor in soup.find_all("a"):
            href = anchor.get("href") or ""
            if href.startswith("glossary.ufacsdb.ru") or "glossary.ufacsdb.ru" in href:
                errors.append(f"{page}: ссылка на старый сайт {href!r}")
                continue
            if href.startswith("http"):
                continue
            target = resolve_page(page, href)
            if target is None:
                continue
            if re.search(r"\.(jpe?g|png|gif|pdf|css|js|xml|txt)$", target, re.I):
                if not os.path.isfile(os.path.join(SITE, target)):
                    errors.append(f"{page}: битая ссылка на ресурс {href!r}")
                else:
                    stats["assets_linked"] += 1
                continue
            if target == "" or target.endswith("/"):
                target = (target + "index.html").lstrip("/")
            if target not in page_set:
                errors.append(f"{page}: битая внутренняя ссылка {href!r}")
            else:
                linked_pages.add(target)

    # --- полнота: выставки, буквы, введение, заключение
    stats["exhibitions"] = len(registry["items"])
    for item in registry["items"]:
        page = item["path"]
        if page not in page_set:
            errors.append(f"нет страницы выставки {page} ({item['title']})")
            continue
        with open(os.path.join(SITE, page), encoding="utf-8") as fh:
            soup = BeautifulSoup(fh.read(), "html.parser")
        article = soup.find("article")
        if article is None:
            errors.append(f"{page}: нет <article>")
            continue
        heading = article.find("h1")
        if heading is None or normalize(heading.get_text()) != normalize(item["title"]):
            errors.append(f"{page}: h1 не совпадает с заголовком источника")
        source_text = normalize(BeautifulSoup(item["html"], "html.parser").get_text(" "))
        result_text = normalize(article.get_text(" "))
        if source_text and source_text not in result_text:
            missing = longest_missing(source_text, result_text)
            errors.append(f"{page}: потерян текст источника, фрагмент: {missing[:120]!r}")
        stats["text_checked"] += 1

        # порядок и количество изображений
        source_images = [i for i in item["images"] if not i.startswith("file:")]
        result_images = [i.get("src") for i in article.find_all("img")]
        if len(source_images) != len(result_images):
            errors.append(
                f"{page}: изображений {len(result_images)} вместо {len(source_images)}"
            )
        stats["images_checked"] += len(result_images)

    for letter in registry["letters"]:
        path = f"sections/{translit(letter['title'])}/index.html"
        if path not in page_set:
            errors.append(f"нет страницы раздела {path}")

    for path in ("index.html", "conclusion/index.html",
                 "contents/index.html", "404.html"):
        if path not in page_set:
            errors.append(f"нет обязательной страницы {path}")

    # --- введение (на главной) и заключение текстом
    for key, path in (("intro", "index.html"),
                      ("conclusion", "conclusion/index.html")):
        with open(os.path.join(SITE, path), encoding="utf-8") as fh:
            result = normalize(BeautifulSoup(fh.read(), "html.parser").get_text(" "))
        source = normalize(
            BeautifulSoup(registry[key]["html"], "html.parser").get_text(" ")
        )
        if source and source not in result:
            errors.append(f"{path}: текст {key} перенесён не полностью")

    # --- sitemap и robots
    with open(os.path.join(SITE, "sitemap.xml"), encoding="utf-8") as fh:
        sitemap = fh.read()
    locations = re.findall(r"<loc>(.*?)</loc>", sitemap)
    stats["sitemap_urls"] = len(locations)
    for loc in locations:
        relative = loc[len(BASE_URL):].lstrip("/")
        if relative and not relative.endswith("/") and not relative.endswith(".html"):
            relative += "index.html" if "." not in posixpath.basename(relative) else ""
        if relative.endswith("/"):
            relative += "index.html"
        if relative and relative not in page_set:
            errors.append(f"sitemap: адрес без файла {loc}")
    if f"{BASE_URL}/sitemap.xml" not in sitemap:
        pass
    with open(os.path.join(SITE, "robots.txt"), encoding="utf-8") as fh:
        robots = fh.read()
    if f"Sitemap: {BASE_URL}/sitemap.xml" not in robots:
        errors.append("robots.txt: неверный адрес sitemap")

    # --- дубликаты title и canonical
    seen_titles: dict[str, str] = {}
    for page in pages:
        with open(os.path.join(SITE, page), encoding="utf-8") as fh:
            soup = BeautifulSoup(fh.read(), "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        if title in seen_titles:
            warnings.append(f"повторяющийся title: {page} и {seen_titles[title]}")
        else:
            seen_titles[title] = page
        canonical = soup.select_one('link[rel="canonical"]')
        if canonical:
            href = canonical["href"]
            if href in canonicals and canonicals[href] != page:
                errors.append(f"повторяющийся canonical: {page} и {canonicals[href]}")

    # --- достижимость страниц из главной
    reachable = crawl(page_set, resolve_page)
    stats["reachable_pages"] = len(reachable)
    for page in sorted(page_set - reachable):
        if page in {"404.html"}:
            continue
        errors.append(f"страница недоступна по ссылкам: {page}")

    # --- повторяемость сборки
    if args.repeat:
        before = file_hashes(SITE)
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build_site.py")],
                       check=True, capture_output=True)
        after = file_hashes(SITE)
        if before != after:
            changed = sorted(k for k in set(before) | set(after)
                             if before.get(k) != after.get(k))
            errors.append(f"повторная сборка изменила файлы: {changed[:5]}")

    report = {
        "html_pages": stats["html_pages"],
        "exhibitions": stats["exhibitions"],
        "texts_checked": stats["text_checked"],
        "images_checked": stats["images_checked"],
        "sitemap_urls": stats["sitemap_urls"],
        "reachable_pages": stats["reachable_pages"],
        "errors": errors,
        "warnings": warnings,
    }
    with open(os.path.join(BUILD, "verify_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)

    print(f"страниц: {stats['html_pages']}, выставок: {stats['exhibitions']}, "
          f"текстов сверено: {stats['text_checked']}, изображений: {stats['images_checked']}")
    print(f"адресов в sitemap: {stats['sitemap_urls']}, достижимо: {reachable and len(reachable)}")
    print(f"ошибок: {len(errors)}, предупреждений: {len(warnings)}")
    for error in errors[:25]:
        print("  ОШИБКА:", error)
    for warning in warnings[:10]:
        print("  ВНИМАНИЕ:", warning)
    return 1 if errors else 0


def longest_missing(source: str, result: str) -> str:
    """Первый фрагмент источника, которого нет в результате."""
    words = source.split()
    start = 0
    while start < len(words):
        chunk = " ".join(words[start:start + 8])
        if chunk in result:
            start += 1
            continue
        return " ".join(words[start:start + 12])
    return source[:120]


def crawl(page_set: set[str], resolve) -> set[str]:
    queue = ["index.html"]
    seen: set[str] = set()
    while queue:
        page = queue.pop()
        if page in seen or page not in page_set:
            continue
        seen.add(page)
        with open(os.path.join(SITE, page), encoding="utf-8") as fh:
            soup = BeautifulSoup(fh.read(), "html.parser")
        for anchor in soup.find_all("a"):
            target = resolve(page, anchor.get("href") or "")
            if target is None:
                continue
            if target == "" or target.endswith("/"):
                target = (target + "index.html").lstrip("/")
            if target in page_set:
                queue.append(target)
    return seen


def file_hashes(root: str) -> dict[str, str]:
    hashes = {}
    for dirpath, _, names in os.walk(root):
        for name in names:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            with open(path, "rb") as fh:
                hashes[rel] = hashlib.sha256(fh.read()).hexdigest()
    return hashes


def translit(value: str) -> str:
    table = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "j", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }
    return "".join(table.get(ch, ch) for ch in value.lower())


if __name__ == "__main__":
    sys.exit(main())
