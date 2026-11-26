#!/usr/bin/env python3
"""Сбор исходного сайта glossary.ufacsdb.ru для переноса глоссария.

Запускается на GitHub Actions (там открытый доступ в интернет) либо локально.
Результат — машиночитаемый реестр в migration/source/:
  pages/<sha1>.html   — сырой HTML каждой страницы;
  manifest.json       — реестр страниц (адрес, родитель, глубина);
  index.json          — список адресов для повторного обхода без сети.

Скрипт идемпотентен: уже сохранённые страницы берутся с диска.
Изображения с исходного сайта не скачиваются — по плану источник
иллюстраций это файлы репозитория.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from collections import deque
from urllib.parse import urljoin, urlsplit, parse_qs

import requests
from bs4 import BeautifulSoup

BASE = "https://glossary.ufacsdb.ru/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "source")
PAGES = os.path.join(SRC, "pages")
DELAY = 0.4
TIMEOUT = 30
MAX_PAGES = 900
UA = (
    "Mozilla/5.0 (compatible; glossary-migration/1.0; "
    "+https://github.com/r2force/glossary)"
)

# Параметры Joomla 1.5, которые не меняют содержание материала.
NOISE_PARAMS = {"tmpl", "print", "layout", "page", "lang", "fontstyle"}


def normalize(url: str) -> str:
    """Канонический вид адреса: убираем шум, сортируем параметры."""
    parts = urlsplit(url)
    query = parse_qs(parts.query, keep_blank_values=True)
    clean = {k: v for k, v in query.items() if k not in NOISE_PARAMS}
    items: list[str] = []
    for key in sorted(clean):
        for value in sorted(clean[key]):
            items.append(f"{key}={value}")
    qs = "&".join(items)
    path = parts.path or "/"
    return f"{parts.scheme}://{parts.netloc}{path}" + (f"?{qs}" if qs else "")


def digest(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def read_cache(url: str) -> str | None:
    name = os.path.join(PAGES, digest(url) + ".html")
    if os.path.exists(name) and os.path.getsize(name) > 0:
        with open(name, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    return None


def write_cache(url: str, text: str) -> None:
    os.makedirs(PAGES, exist_ok=True)
    name = os.path.join(PAGES, digest(url) + ".html")
    with open(name, "w", encoding="utf-8") as fh:
        fh.write(text)


def is_internal(href: str) -> bool:
    host = urlsplit(href).netloc.lower()
    return not host or host in {"glossary.ufacsdb.ru", "www.glossary.ufacsdb.ru"}


def interesting(url: str) -> bool:
    """Оставляем только страницы, которые могут содержать материал."""
    return True


def main() -> int:
    os.makedirs(PAGES, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = UA

    seen: dict[str, dict] = {}
    queue: deque[tuple[str, str | None, int]] = deque([(BASE, None, 0)])
    failures: list[dict] = []

    if os.path.exists(os.path.join(SRC, "manifest.json")):
        with open(os.path.join(SRC, "manifest.json"), encoding="utf-8") as fh:
            for item in json.load(fh):
                seen[item["url"]] = item

    while queue and len(seen) < MAX_PAGES:
        url, parent, depth = queue.popleft()
        if url in seen and seen[url].get("status") == "ok":
            continue
        cached = read_cache(url)
        if cached is not None:
            html, status = cached, 200
        else:
            try:
                response = session.get(url, timeout=TIMEOUT, allow_redirects=True)
                status = response.status_code
                response.encoding = response.apparent_encoding or "utf-8"
                html = response.text
                if status != 200:
                    failures.append({"url": url, "status": status})
                    seen[url] = {
                        "url": url,
                        "parent": parent,
                        "depth": depth,
                        "status": f"http-{status}",
                    }
                    continue
                write_cache(url, html)
                time.sleep(DELAY)
            except Exception as exc:  # noqa: BLE001
                failures.append({"url": url, "error": repr(exc)})
                seen[url] = {
                    "url": url,
                    "parent": parent,
                    "depth": depth,
                    "status": "error",
                    "error": repr(exc),
                }
                continue

        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        text_len = len(soup.get_text(" ", strip=True))
        seen[url] = {
            "url": url,
            "parent": parent,
            "depth": depth,
            "status": "ok",
            "title": title,
            "file": digest(url) + ".html",
            "bytes": len(html.encode("utf-8")),
            "text_length": text_len,
        }

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()
            if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
                continue
            absolute = urljoin(url, href)
            if not absolute.startswith("http"):
                continue
            if not is_internal(absolute):
                continue
            absolute = absolute.split("#")[0]
            if not absolute:
                continue
            target = normalize(absolute)
            if ".jpg" in target.lower() or ".png" in target.lower():
                continue
            if "/images/" in target or "/media/" in target or "/templates/" in target:
                continue
            if target in seen:
                continue
            if depth < 4 and interesting(target):
                queue.append((target, url, depth + 1))

    ordered = [seen[k] for k in sorted(seen)]
    with open(os.path.join(SRC, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(ordered, fh, ensure_ascii=False, indent=1, sort_keys=True)
    with open(os.path.join(SRC, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(
            {
                "base": BASE,
                "pages": len(ordered),
                "ok": sum(1 for p in ordered if p.get("status") == "ok"),
                "failures": failures,
            },
            fh,
            ensure_ascii=False,
            indent=1,
        )
    print(
        f"собрано {len(ordered)} адресов, "
        f"успешно {sum(1 for p in ordered if p.get('status') == 'ok')}, "
        f"ошибок {len(failures)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
