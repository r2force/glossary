#!/usr/bin/env python3
"""Единственный источник общей разметки сайта (принцип DRY).

Файлы в `migration/templates/` содержат шапку, подвал, алфавитный указатель,
хлебные крошки, карточки, переходы между выставками, `<head>` и стили.
`build_site.py` только подставляет в них данные: опубликованные страницы
остаются самодостаточным статическим HTML (без JS-инклюдов и SSI), но любая
правка общего блока делается один раз и попадает сразу на все 300+ страниц.

Значения, которые вставляются в шаблон, экранируются в функциях ниже;
готовые HTML-блоки (`body`, `extra_head`, `header`, `footer`, `meta`)
передаются как есть.
"""
from __future__ import annotations

import html
import os
import posixpath
from string import Template

MIGRATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(MIGRATION, "templates")

SITE_TITLE = "«Книга – Выставка – Читатель»"
SITE_SUBTITLE = "глоссарий нетрадиционных форм книжных выставок"
ORG = "Центральная городская детская библиотека г. Уфы"
BASE_URL = os.environ.get("SITE_BASE_URL", "https://r2force.github.io/glossary")

# Буквы, показанные в алфавитном указателе: на источнике нет Ё, Й, Щ, Ъ, Ы, Ь.
LETTERS = "АБВГДЕЖЗИКЛМНОПРСТУФХЦЧШЭЮЯ"

# Верхнее меню: один список для всех страниц.
NAV = (
    ("index.html", "Главная"),
    ("contents/index.html", "Указатель"),
    ("conclusion/index.html", "Заключение"),
)

_TEMPLATE_CACHE: dict[str, Template] = {}


def esc(value: str) -> str:
    return html.escape(str(value), quote=True)


def render(name: str, **values: str) -> str:
    """Подстановка в шаблон из migration/templates/ (путь относительно каталога)."""
    path = os.path.join(TEMPLATES, name)
    if path not in _TEMPLATE_CACHE:
        with open(path, encoding="utf-8") as fh:
            _TEMPLATE_CACHE[path] = Template(fh.read().rstrip("\n"))
    return _TEMPLATE_CACHE[path].substitute(values)


def indent(block: str, prefix: str = "    ") -> str:
    return "\n".join(prefix + line if line else line for line in block.split("\n"))


# ---------------------------------------------------------------- адреса

def url_for(from_path: str, to_path: str) -> str:
    """Относительный адрес между двумя файлами сайта (без обращения к ФС)."""
    start = posixpath.dirname(from_path) or "."
    return posixpath.relpath("/" + to_path.lstrip("/"), "/" + start).lstrip("/")


def page_url(path: str) -> str:
    """Канонический адрес страницы на GitHub Pages."""
    if path.endswith("index.html"):
        directory = os.path.dirname(path)
        return f"{BASE_URL}/" + (directory + "/" if directory else "")
    return f"{BASE_URL}/{path}"


# ---------------------------------------------------------------- общие блоки

def head_meta(title: str, description: str, canonical: str) -> str:
    return render(
        "partials/head.html",
        title=esc(title),
        description=esc(description),
        canonical=esc(canonical),
    )


def header(current: str) -> str:
    links = []
    for path, label in NAV:
        current_attr = ' aria-current="page"' if path == current else ""
        links.append(
            f'<a href="{esc(url_for(current, path))}"{current_attr}>{esc(label)}</a>'
        )
    return render(
        "partials/header.html",
        home=esc(url_for(current, "index.html")),
        site_title=esc(SITE_TITLE),
        site_subtitle=esc(SITE_SUBTITLE),
        links="\n      ".join(links),
    )


def footer() -> str:
    return render(
        "partials/footer.html",
        site_title=esc(SITE_TITLE),
        site_subtitle=esc(SITE_SUBTITLE),
        org=esc(ORG),
    )


def letter_nav(path: str, letter_path: dict[str, str], current: str = "") -> str:
    """Алфавит со ссылками: один шаблон для главной, указателя и разделов."""
    items = []
    for letter in LETTERS:
        target = letter_path.get(letter)
        if not target:
            items.append(f'<li><span class="off">{letter}</span></li>')
            continue
        current_attr = ' aria-current="page"' if letter == current else ""
        items.append(
            f'<li><a href="{esc(url_for(path, target))}"{current_attr}>{letter}</a></li>'
        )
    return render("partials/letter-nav.html", items="".join(items))


def breadcrumbs(path: str, links: list[tuple[str, str]]) -> str:
    items = " · ".join(
        f'<a href="{esc(url_for(path, target))}">{esc(label)}</a>'
        for label, target in links
    )
    return render("partials/breadcrumbs.html", items=items)


def cards(path: str, entries: list[tuple[str, str, str]]) -> str:
    """Список карточек: (заголовок, путь страницы, краткое описание)."""
    items = []
    for title, target, preview in entries:
        items.append(
            render(
                "partials/card.html",
                href=esc(url_for(path, target)),
                title=esc(title),
                preview=f"<p>{esc(preview)}</p>" if preview else "",
            )
        )
    return render("partials/cards.html", items="".join(items))


def pager(path: str, previous: dict | None, following: dict | None) -> str:
    def link(item: dict | None, arrow: str, tail: bool) -> str:
        if not item:
            return ""
        inner = f'<a href="{esc(url_for(path, item["path"]))}">{esc(item["title"])}</a>'
        return f"{arrow} {inner}" if tail else f"{inner} {arrow}"

    return render(
        "partials/pager.html",
        prev=link(previous, "←", tail=True),
        next=link(following, "→", tail=False),
    )


def article(title: str, body: str, pager_html: str = "") -> str:
    return render(
        "partials/article.html",
        title=esc(title),
        body=body,
        pager="\n" + pager_html if pager_html else "",
    )


def layout(path: str, title: str, description: str, body: str,
           canonical: str, extra_head: str = "") -> str:
    return render(
        "page.html",
        title=esc(title),
        meta=head_meta(title, description, canonical),
        stylesheet=esc(url_for(path, "assets/site.css")),
        extra_head=extra_head,
        header=header(path),
        body=indent(body),
        footer=footer(),
    ) + "\n"


def stylesheet() -> str:
    with open(os.path.join(TEMPLATES, "site.css"), encoding="utf-8") as fh:
        return fh.read().strip() + "\n"
