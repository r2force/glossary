#!/usr/bin/env python3
"""Независимая проверка исходников Jekyll (site/) и собранного сайта (_site/).

Проверяет:
  * архитектуру Jekyll и DRY в site/: шаблоны в site/_layouts и site/_includes,
    меню в site/_data/navigation.yml + site/_includes/nav.html, отсутствие
    дублирующего каркаса (<!DOCTYPE>, <header>, <footer>, <nav>) в контенте;
  * полноту собранного _site/: каждая запись реестра имеет страницу, тексты дословны;
  * изображения: файл существует в _site/, регистр совпадает, осмысленный alt;
  * ссылки: внутренние адреса существуют с учётом baseurl (/glossary);
  * HTML и SEO: title, description, canonical, один h1, lang=ru, JSON-LD;
  * единообразие шапки, меню, подвала и алфавита на всех собранных страницах;
  * sitemap.xml, robots.txt, 404.html и достижимость страниц по ссылкам;
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
import shlex
import subprocess
import sys
import urllib.parse
from collections import Counter

import yaml
from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
SOURCE_SITE = os.path.join(REPO, "site")
DEFAULT_BUILT = os.path.join(REPO, "_site")
BUILD = os.path.join(ROOT, "build")

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
CHROME_IN_CONTENT = re.compile(
    r"<!doctype\b|<html\b|<head\b|<body\b|<header\b|<footer\b|"
    r"<nav\s+class=[\"'](?:main|crumbs|pager)[\"']",
    re.I,
)


def normalize(text: str) -> str:
    text = html.unescape(text or "")
    text = text.replace("\xa0", " ").replace("\u200b", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_front_matter(text: str) -> tuple[dict | None, str]:
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    if end == -1:
        return None, text
    raw_fm = text[4:end]
    rest = text[end + 4:].lstrip("\n")
    data = yaml.safe_load(raw_fm)
    return ({} if data is None else data), rest


def check_jekyll_source() -> tuple[list[str], dict, list[dict], list[str]]:
    """Проверка устройства Jekyll-проекта в site/ (DRY и разделение слоёв)."""
    errors: list[str] = []

    if os.path.exists(os.path.join(ROOT, "templates")):
        errors.append("migration/templates не должен существовать: шаблоны лежат в site/")
    for stale in ("exhibitions", "sections", "introduction"):
        if os.path.exists(os.path.join(SOURCE_SITE, stale)):
            errors.append(f"site/{stale}: сгенерированный HTML не должен храниться в site/")

    required = [
        "_config.yml",
        "_data/navigation.yml",
        "_data/alphabet.yml",
        "_layouts/default.html",
        "_layouts/home.html",
        "_layouts/article.html",
        "_layouts/section.html",
        "_layouts/exhibition.html",
        "_includes/head.html",
        "_includes/header.html",
        "_includes/nav.html",
        "_includes/footer.html",
        "_includes/breadcrumbs.html",
        "_includes/letter-nav.html",
        "_includes/cards.html",
        "_includes/pager.html",
        "assets/site.css",
        "sitemap.xml",
        "robots.txt",
        "404.html",
        "index.html",
        "contents/index.html",
        "conclusion/index.html",
    ]
    for rel in required:
        if not os.path.isfile(os.path.join(SOURCE_SITE, rel)):
            errors.append(f"site/{rel}: отсутствует обязательный файл Jekyll")

    config: dict = {}
    nav: list[dict] = []
    alphabet: list[str] = []
    cfg_path = os.path.join(SOURCE_SITE, "_config.yml")
    if os.path.isfile(cfg_path):
        with open(cfg_path, encoding="utf-8") as fh:
            config = yaml.safe_load(fh) or {}
    nav_path = os.path.join(SOURCE_SITE, "_data/navigation.yml")
    if os.path.isfile(nav_path):
        with open(nav_path, encoding="utf-8") as fh:
            nav = yaml.safe_load(fh) or []
    alpha_path = os.path.join(SOURCE_SITE, "_data/alphabet.yml")
    if os.path.isfile(alpha_path):
        with open(alpha_path, encoding="utf-8") as fh:
            alphabet = yaml.safe_load(fh) or []

    header_inc = os.path.join(SOURCE_SITE, "_includes/header.html")
    nav_inc = os.path.join(SOURCE_SITE, "_includes/nav.html")
    if os.path.isfile(header_inc):
        with open(header_inc, encoding="utf-8") as fh:
            if "include nav.html" not in fh.read():
                errors.append("site/_includes/header.html должен подключать nav.html")
    if os.path.isfile(nav_inc):
        with open(nav_inc, encoding="utf-8") as fh:
            if "site.data.navigation" not in fh.read():
                errors.append("site/_includes/nav.html должен читать site.data.navigation")

    content_files = ["index.html", "conclusion/index.html", "contents/index.html", "404.html"]
    for folder in ("_exhibitions", "_sections"):
        full_dir = os.path.join(SOURCE_SITE, folder)
        if os.path.isdir(full_dir):
            for name in sorted(os.listdir(full_dir)):
                if name.endswith((".html", ".md")):
                    content_files.append(f"{folder}/{name}")

    for rel in content_files:
        full = os.path.join(SOURCE_SITE, rel)
        if not os.path.isfile(full):
            continue
        with open(full, encoding="utf-8") as fh:
            raw = fh.read()
        fm, body = split_front_matter(raw)
        if fm is None:
            errors.append(f"site/{rel}: отсутствует YAML front matter")
            continue
        if CHROME_IN_CONTENT.search(body):
            errors.append(f"site/{rel}: в содержательном файле найден HTML-каркас оформления")
        if WORD_MARKUP.search(body):
            errors.append(f"site/{rel}: осталась разметка Word/Joomla")

    return errors, config, nav, alphabet


def page_files(built_dir: str) -> list[str]:
    found = []
    for dirpath, _, names in os.walk(built_dir):
        if os.sep + "images" + os.sep in dirpath + os.sep:
            continue
        for name in names:
            if name.endswith(".html"):
                found.append(os.path.relpath(os.path.join(dirpath, name), built_dir)
                             .replace(os.sep, "/"))
    return sorted(found)


def all_html_files(built_dir: str) -> list[str]:
    found = []
    for dirpath, _, names in os.walk(built_dir):
        for name in names:
            if name.endswith(".html"):
                found.append(os.path.relpath(os.path.join(dirpath, name), built_dir)
                             .replace(os.sep, "/"))
    return sorted(found)


def check_legacy_html(built_dir: str, path: str) -> list[str]:
    problems = []
    with open(os.path.join(built_dir, path), encoding="utf-8") as fh:
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


def page_url_path(rel_page: str) -> str:
    if rel_page == "index.html":
        return "/"
    if rel_page.endswith("/index.html"):
        return "/" + rel_page[:-len("index.html")]
    return "/" + rel_page


def check_shared_blocks(path: str, soup: BeautifulSoup, baseurl: str,
                        nav_items: list[dict], alphabet: list[str],
                        active_letters: dict[str, str]) -> list[str]:
    """Проверка единообразия шапки, меню, подвала и алфавита."""
    problems = []
    headers = soup.select("header.site")
    footers = soup.select("footer.site")
    if len(headers) != 1 or len(footers) != 1:
        problems.append(f"{path}: нарушена единственность header.site / footer.site")
        return problems

    nav = headers[0].select_one("nav.main")
    if nav is None:
        problems.append(f"{path}: нет <nav class=\"main\"> в шапке")
    else:
        links = nav.find_all("a")
        expected = [
            (f"{baseurl}{item['url']}", item["title"], item["url"] == page_url_path(path))
            for item in nav_items
        ]
        got = [
            (a.get("href"), a.get_text(strip=True), a.get("aria-current") == "page")
            for a in links
        ]
        if got != expected:
            problems.append(f"{path}: верхнее меню {got} не совпадает с navigation.yml {expected}")

    alpha_nodes = soup.select("ul.letter-nav")
    if len(alpha_nodes) > 1:
        problems.append(f"{path}: алфавитный указатель продублирован")
    if alpha_nodes and not (path in {"index.html", "contents/index.html"}
                            or path.startswith("sections/")):
        problems.append(f"{path}: алфавитный указатель на лишней странице")
    if alpha_nodes:
        items = alpha_nodes[0].find_all("li", recursive=False)
        if len(items) != len(alphabet):
            problems.append(f"{path}: букв в указателе {len(items)} вместо {len(alphabet)}")
        else:
            current_slug = path.split("/")[1] if path.startswith("sections/") else ""
            for li, letter in zip(items, alphabet):
                slug = active_letters.get(letter)
                a = li.find("a")
                if slug:
                    expected_href = f"{baseurl}/sections/{slug}/"
                    is_cur = slug == current_slug
                    if a is None or a.get("href") != expected_href or a.get_text(strip=True) != letter:
                        problems.append(f"{path}: неверная ссылка буквы {letter}")
                    elif (a.get("aria-current") == "page") != is_cur:
                        problems.append(f"{path}: неверный aria-current у буквы {letter}")
                else:
                    span = li.find("span", class_="off")
                    if a is not None or span is None or span.get_text(strip=True) != letter:
                        problems.append(f"{path}: неактивная буква {letter} оформлена неверно")
    return problems


def default_build_command(built_dir: str) -> list[str]:
    return [
        "bundle", "exec", "jekyll", "build",
        "--source", SOURCE_SITE,
        "--destination", built_dir,
        "--strict_front_matter",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default=DEFAULT_BUILT,
                        help="каталог собранного статического сайта (по умолчанию _site)")
    parser.add_argument("--repeat", action="store_true",
                        help="пересобрать сайт и сравнить хеши файлов")
    parser.add_argument("--build-cmd", default="",
                        help="команда пересборки для --repeat (по умолчанию bundle exec jekyll build)")
    args = parser.parse_args()

    built_dir = os.path.abspath(args.site)
    errors: list[str] = []
    warnings: list[str] = []
    stats: Counter = Counter()

    src_errors, config, nav_items, alphabet = check_jekyll_source()
    errors.extend(src_errors)

    if not os.path.isdir(built_dir):
        errors.append(f"каталог собранного сайта не найден: {built_dir}")
        for err in errors:
            print("  ОШИБКА:", err)
        return 1

    baseurl = (config.get("baseurl") or "").rstrip("/")
    site_url = (config.get("url") or "https://r2force.github.io").rstrip("/") + baseurl

    with open(os.path.join(BUILD, "registry.json"), encoding="utf-8") as fh:
        registry = json.load(fh)

    active_letters = {
        letter["title"]: translit(letter["title"]) for letter in registry["letters"]
    }

    pages = page_files(built_dir)
    stats["html_pages"] = len(pages)
    page_set = set(pages)

    for path in all_html_files(built_dir):
        errors.extend(check_legacy_html(built_dir, path))

    def resolve_page(from_page: str, target: str) -> str | None:
        if not target or target.startswith(("http:", "https:", "mailto:", "#", "data:")):
            return None
        raw_path = urllib.parse.unquote(target.split("#")[0].split("?")[0])
        if not raw_path:
            return None
        if raw_path.startswith("/"):
            if baseurl:
                if raw_path == baseurl or raw_path.startswith(baseurl + "/"):
                    rel = raw_path[len(baseurl):].lstrip("/")
                else:
                    return f"__missing_baseurl__:{target}"
            else:
                rel = raw_path.lstrip("/")
            return rel
        joined = posixpath.normpath(posixpath.join(posixpath.dirname(from_page), raw_path))
        return "" if joined == "." else joined

    canonicals: dict[str, str] = {}
    seen_titles: dict[str, str] = {}

    for page in pages:
        with open(os.path.join(built_dir, page), encoding="utf-8") as fh:
            text = fh.read()
        soup = BeautifulSoup(text, "html.parser")
        stats["documents"] += 1
        errors.extend(
            check_shared_blocks(page, soup, baseurl, nav_items, alphabet, active_letters)
        )

        if soup.html is None or (soup.html.get("lang") or "")[:2] != "ru":
            errors.append(f"{page}: нет <html lang=\"ru\">")
        if soup.select_one("meta[charset], meta[http-equiv=content-type]") is None:
            errors.append(f"{page}: не указана кодировка")
        title_tag = soup.title.get_text(strip=True) if soup.title else ""
        if not title_tag:
            errors.append(f"{page}: пустой <title>")
        elif title_tag in seen_titles:
            warnings.append(f"повторяющийся title: {page} и {seen_titles[title_tag]}")
        else:
            seen_titles[title_tag] = page

        description = soup.select_one('meta[name="description"]')
        if description is None or not description.get("content", "").strip():
            errors.append(f"{page}: пустой meta description")
        canonical = soup.select_one('link[rel="canonical"]')
        if canonical is None or not canonical.get("href", "").startswith("https://"):
            errors.append(f"{page}: нет абсолютного canonical")
        else:
            href = canonical["href"]
            if href in canonicals and canonicals[href] != page:
                errors.append(f"повторяющийся canonical: {page} и {canonicals[href]}")
            canonicals.setdefault(href, page)

        h1 = soup.find_all("h1")
        if len(h1) != 1:
            errors.append(f"{page}: заголовков h1 — {len(h1)}")
        if soup.select_one('meta[name="robots"][content*="noindex"]'):
            errors.append(f"{page}: неожиданный noindex")
        if soup.select_one("script[src]"):
            errors.append(f"{page}: внешний скрипт, текст должен быть в HTML")

        for img in soup.find_all("img"):
            src = img.get("src") or ""
            target = resolve_page(page, src)
            if target is None or target.startswith("__missing_baseurl__:"):
                errors.append(f"{page}: некорректный src изображения {src!r}")
                continue
            full = os.path.join(built_dir, target)
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
            if "glossary.ufacsdb.ru" in href:
                errors.append(f"{page}: ссылка на старый сайт {href!r}")
                continue
            if href.startswith("http"):
                continue
            target = resolve_page(page, href)
            if target is None:
                continue
            if target.startswith("__missing_baseurl__:"):
                errors.append(f"{page}: ссылка без baseurl ({baseurl}): {href!r}")
                continue
            if re.search(r"\.(jpe?g|png|gif|pdf|css|js|xml|txt)$", target, re.I):
                if not os.path.isfile(os.path.join(built_dir, target)):
                    errors.append(f"{page}: битая ссылка на ресурс {href!r}")
                else:
                    stats["assets_linked"] += 1
                continue
            if target == "" or target.endswith("/"):
                target = (target + "index.html").lstrip("/")
            if target not in page_set:
                errors.append(f"{page}: битая внутренняя ссылка {href!r}")

    stats["exhibitions"] = len(registry["items"])
    for item in registry["items"]:
        page = item["path"]
        if page not in page_set:
            errors.append(f"нет страницы выставки {page} ({item['title']})")
            continue
        with open(os.path.join(built_dir, page), encoding="utf-8") as fh:
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

    for path in ("index.html", "conclusion/index.html", "contents/index.html", "404.html"):
        if path not in page_set:
            errors.append(f"нет обязательной страницы {path}")

    for key, path in (("intro", "index.html"), ("conclusion", "conclusion/index.html")):
        if path not in page_set:
            continue
        with open(os.path.join(built_dir, path), encoding="utf-8") as fh:
            result = normalize(BeautifulSoup(fh.read(), "html.parser").get_text(" "))
        source = normalize(
            BeautifulSoup(registry[key]["html"], "html.parser").get_text(" ")
        )
        if source and source not in result:
            errors.append(f"{path}: текст {key} перенесён не полностью")

    sitemap_path = os.path.join(built_dir, "sitemap.xml")
    if not os.path.isfile(sitemap_path):
        errors.append("нет собранного файла sitemap.xml")
    else:
        with open(sitemap_path, encoding="utf-8") as fh:
            sitemap = fh.read()
        locations = re.findall(r"<loc>(.*?)</loc>", sitemap)
        stats["sitemap_urls"] = len(locations)
        for loc in locations:
            if not loc.startswith(site_url + "/") and loc != site_url:
                errors.append(f"sitemap: неверный префикс адреса {loc}")
                continue
            relative = loc[len(site_url):].lstrip("/")
            if not relative or relative.endswith("/"):
                relative = (relative + "index.html").lstrip("/")
            if relative not in page_set:
                errors.append(f"sitemap: адрес без файла {loc}")

    robots_path = os.path.join(built_dir, "robots.txt")
    if not os.path.isfile(robots_path):
        errors.append("нет собранного файла robots.txt")
    else:
        with open(robots_path, encoding="utf-8") as fh:
            robots = fh.read()
        if f"Sitemap: {site_url}/sitemap.xml" not in robots:
            errors.append("robots.txt: неверный адрес sitemap")

    reachable = crawl(built_dir, page_set, resolve_page)
    stats["reachable_pages"] = len(reachable)
    for page in sorted(page_set - reachable):
        if page in {"404.html"}:
            continue
        errors.append(f"страница недоступна по ссылкам: {page}")

    if args.repeat:
        before = file_hashes(built_dir)
        cmd = shlex.split(args.build_cmd) if args.build_cmd else default_build_command(built_dir)
        env = os.environ.copy()
        if not args.build_cmd:
            env.setdefault("BUNDLE_GEMFILE", os.path.join(SOURCE_SITE, "Gemfile"))
        subprocess.run(cmd, check=True, capture_output=True, env=env)
        after = file_hashes(built_dir)
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
    print(f"адресов в sitemap: {stats['sitemap_urls']}, достижимо: {len(reachable)}")
    print(f"ошибок: {len(errors)}, предупреждений: {len(warnings)}")
    for error in errors[:25]:
        print("  ОШИБКА:", error)
    for warning in warnings[:10]:
        print("  ВНИМАНИЕ:", warning)
    return 1 if errors else 0


def longest_missing(source: str, result: str) -> str:
    words = source.split()
    start = 0
    while start < len(words):
        chunk = " ".join(words[start:start + 8])
        if chunk in result:
            start += 1
            continue
        return " ".join(words[start:start + 12])
    return source[:120]


def crawl(built_dir: str, page_set: set[str], resolve) -> set[str]:
    queue = ["index.html"]
    seen: set[str] = set()
    while queue:
        page = queue.pop()
        if page in seen or page not in page_set:
            continue
        seen.add(page)
        with open(os.path.join(built_dir, page), encoding="utf-8") as fh:
            soup = BeautifulSoup(fh.read(), "html.parser")
        for anchor in soup.find_all("a"):
            target = resolve(page, anchor.get("href") or "")
            if target is None or target.startswith("__missing_baseurl__:"):
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
