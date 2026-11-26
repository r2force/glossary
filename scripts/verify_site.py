#!/usr/bin/env python3
"""Verify a Jekyll build against its current editable sources, without an archive.

Run: python scripts/verify_site.py --source site --site _site --repeat
Only literal {{ '/path' | relative_url }} expressions are expanded when comparing
article bodies. Templates are rendered by Jekyll, never by this verifier.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import urllib.parse
import xml.etree.ElementTree as ET

import yaml
from bs4 import BeautifulSoup, Comment, NavigableString, Tag

REPO = Path(__file__).resolve().parents[1]
RELATIVE_URL = re.compile(r"\{\{\s*(['\"])(.*?)\1\s*\|\s*relative_url\s*\}\}")
LEGACY_TAGS = set('font center big small strike s tt u b i marquee blink dir menu acronym applet basefont frame frameset noframes isindex o:p xml'.split())
LEGACY_ATTRS = set('style bgcolor align valign cellpadding cellspacing border bordercolor color face size hspace vspace nowrap background clear language mce_src mce_href width height'.split())
CHROME = re.compile(r'<!doctype\b|<(?:html|head|body|header|footer|nav)\b', re.I)
WORD = re.compile(r'mso-|class\s*=\s*[\"\'][^\"\']*Mso|<!--\s*\[if|<o:p|<w:|<v:|<\?xml|font-family', re.I)
SIGNIFICANT_ATTRS = ('href', 'src', 'alt', 'title', 'colspan', 'rowspan', 'scope', 'id', 'name', 'start', 'value', 'type')


def normalize(value):
    return re.sub(r'\s+', ' ', html.unescape(str(value)).replace('\xa0', ' ').replace('\u200b', '')).strip()


def split_front_matter(raw):
    match = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)', raw, re.S)
    if not match:
        raise ValueError('отсутствует YAML front matter')
    metadata = yaml.safe_load(match.group(1)) or {}
    if not isinstance(metadata, dict):
        raise ValueError('front matter должен быть объектом')
    return metadata, raw[match.end():]


def render_content(body, baseurl):
    body = RELATIVE_URL.sub(lambda m: baseurl + '/' + m.group(2).lstrip('/'), body)
    if '{{' in body or '{%' in body:
        raise ValueError('в содержимом поддерживается только literal relative_url; шаблоны должны находиться в _layouts/_includes')
    return body


def signature(node):
    """Ordered DOM events preserve structure, links, captions and image positions."""
    events = []
    for child in node.children:
        if isinstance(child, Comment):
            continue
        if isinstance(child, NavigableString):
            text = normalize(child)
            if text:
                events.append(('text', text))
        elif isinstance(child, Tag):
            attrs = tuple((key, normalize(child[key])) for key in SIGNIFICANT_ATTRS if key in child.attrs)
            events.append(('open', child.name, attrs))
            events.extend(signature(child))
            events.append(('close', child.name))
    return events


def page_path(url):
    if not url.startswith('/') or '?' in url or '#' in url or '..' in url.split('/'):
        raise ValueError(f'неподдерживаемый постоянный адрес {url!r}')
    return (url.lstrip('/') + 'index.html') if url.endswith('/') else url.lstrip('/')


def canonical_path(page):
    if page == 'index.html':
        return '/'
    return '/' + (page[:-len('index.html')] if page.endswith('/index.html') else page)


def exact_file(root, relative):
    """Check every component, including on a case-insensitive filesystem."""
    current = root
    parts = Path(relative).parts
    if not parts or any(part in ('..', '/', '') for part in parts):
        return False
    for part in parts:
        if not current.is_dir() or part not in os.listdir(current):
            return False
        current = current / part
        if current.is_symlink():
            return False
    return current.is_file()


def inventory(source, config, errors):
    docs = {}
    for path in sorted(source.rglob('*.html')):
        rel = path.relative_to(source)
        if any(part.startswith('.') for part in rel.parts):
            continue
        collection = rel.parts[0][1:] if rel.parts[0] in ('_exhibitions', '_sections') else None
        if not collection and (rel.parts[0].startswith('_') or rel.parts[0] in ('images', 'assets', 'vendor')):
            continue
        try:
            fm, body = split_front_matter(path.read_text(encoding='utf-8'))
            if collection:
                if any(not isinstance(fm.get(key), str) or not fm[key].strip() for key in ('title', 'letter')):
                    raise ValueError('у материала коллекции обязательны непустые строки title и letter')
                if not isinstance(fm.get('order'), int) or isinstance(fm['order'], bool):
                    raise ValueError('у материала коллекции обязателен целочисленный order')
                permalink = fm.get('permalink') or config.get('collections', {}).get(collection, {}).get('permalink')
                if not permalink:
                    raise ValueError(f'нет permalink для коллекции {collection}')
                slug = str(fm.get('slug') or path.stem)
                url = str(permalink).replace(':name', slug).replace(':slug', slug)
                if ':' in url:
                    raise ValueError(f'неподдерживаемый permalink {url}')
            else:
                url = fm.get('permalink') or canonical_path(rel.as_posix())
            target = page_path(url)
            if target in docs:
                raise ValueError(f'коллизия адресов: {target}')
            if CHROME.search(body) and (collection or rel.as_posix() in ('index.html', 'conclusion/index.html')):
                errors.append(f'{rel}: каркас оформления находится в содержимом')
            if WORD.search(body):
                errors.append(f'{rel}: разметка Word/Joomla')
            docs[target] = {'source': rel.as_posix(), 'fm': fm, 'body': body, 'collection': collection}
        except (ValueError, yaml.YAMLError, OSError) as exc:
            errors.append(f'{rel}: {exc}')
    for path in ('index.html', 'contents/index.html', 'conclusion/index.html', '404.html'):
        if path not in docs:
            errors.append(f'нет обязательного исходного материала {path}')
    sections = [doc for doc in docs.values() if doc['collection'] == 'sections']
    letters = [doc['fm']['letter'] for doc in sections]
    if len(letters) != len(set(letters)):
        errors.append('повторяющиеся буквы разделов')
    for doc in docs.values():
        if doc['collection'] == 'exhibitions' and doc['fm']['letter'] not in letters:
            errors.append(f"{doc['source']}: нет раздела буквы {doc['fm']['letter']}")
    if not any(doc['collection'] == 'exhibitions' for doc in docs.values()):
        errors.append('коллекция выставок пуста')
    return docs


def check_architecture(source, errors):
    required = ['_config.yml', '_data/navigation.yml', '_data/alphabet.yml', 'assets/site.css', 'sitemap.xml', 'robots.txt']
    required += [f'_layouts/{name}.html' for name in ('default', 'home', 'article', 'section', 'exhibition')]
    required += [f'_includes/{name}.html' for name in ('head', 'header', 'nav', 'footer', 'breadcrumbs', 'letter-nav', 'cards', 'pager')]
    for rel in required:
        if not exact_file(source, rel):
            errors.append(f'source/{rel}: отсутствует обязательный файл')
    for rel in ('exhibitions', 'sections', 'introduction'):
        if (source / rel).exists():
            errors.append(f'source/{rel}: собранный HTML должен находиться вне исходников')
    for rel, marker in (('_includes/header.html', 'include nav.html'), ('_includes/nav.html', 'site.data.navigation')):
        if (source / rel).is_file() and marker not in (source / rel).read_text(encoding='utf-8'):
            errors.append(f'source/{rel}: отсутствует {marker}')


def verify(source, built):
    source, built = Path(source).resolve(), Path(built).resolve()
    errors = []
    report = {'html_pages': 0, 'exhibitions': 0, 'texts_checked': 0, 'images_checked': 0, 'sitemap_urls': 0, 'reachable_pages': 0, 'errors': errors, 'warnings': []}
    check_architecture(source, errors)
    try:
        config = yaml.safe_load((source / '_config.yml').read_text()) or {}
        nav_items = yaml.safe_load((source / '_data/navigation.yml').read_text()) or []
        alphabet = yaml.safe_load((source / '_data/alphabet.yml').read_text()) or []
    except (OSError, yaml.YAMLError) as exc:
        errors.append(f'не удалось прочитать конфигурацию: {exc}')
        return report
    baseurl = str(config.get('baseurl') or '').rstrip('/')
    origin = str(config.get('url') or '').rstrip('/')
    if not origin.startswith('https://'):
        errors.append('url сайта должен быть абсолютным HTTPS-адресом')
    site_url = origin + baseurl
    docs = inventory(source, config, errors)
    report['exhibitions'] = sum(doc['collection'] == 'exhibitions' for doc in docs.values())
    if not built.is_dir():
        errors.append(f'нет каталога сборки {built}')
        return report
    pages = {p.relative_to(built).as_posix(): BeautifulSoup(p.read_text(encoding='utf-8'), 'html.parser') for p in sorted(built.rglob('*.html'))}
    report['html_pages'] = len(pages)
    for page in sorted(set(docs) - set(pages)):
        errors.append(f'нет собранной страницы {page}')
    for page in sorted(set(pages) - set(docs)):
        errors.append(f'страница не имеет текущего исходника: {page}')

    def local_target(page, href):
        parsed = urllib.parse.urlsplit(href)
        if parsed.scheme.lower() in ('javascript', 'file', 'vbscript'):
            raise ValueError(f'запрещённая схема ссылки: {href}')
        if parsed.scheme and parsed.scheme not in ('http', 'https'):
            return None
        if parsed.netloc and (parsed.scheme or 'https', parsed.netloc) != (urllib.parse.urlsplit(origin).scheme, urllib.parse.urlsplit(origin).netloc):
            return None
        raw = urllib.parse.unquote(parsed.path)
        if raw.startswith('/'):
            if baseurl and raw != baseurl and not raw.startswith(baseurl + '/'):
                raise ValueError(f'ссылка без префикса {baseurl}: {href}')
            rel = raw[len(baseurl):].lstrip('/') if baseurl else raw.lstrip('/')
        elif not raw:
            rel = page
        else:
            rel = os.path.normpath(str(Path(page).parent / raw)).replace(os.sep, '/')
        if rel == '..' or rel.startswith('../') or rel.startswith('/'):
            raise ValueError(f'ссылка за пределами сайта: {href}')
        if not rel or rel.endswith('/'):
            rel += 'index.html'
        # normpath removes a trailing slash from document-relative URLs.
        elif raw.endswith('/'):
            rel += '/index.html'
        return rel, urllib.parse.unquote(parsed.fragment)

    titles, descriptions = {}, {}
    graph = {page: set() for page in pages}
    header_signatures, footer_signatures = set(), set()
    active_letters = {doc['fm']['letter']: path for path, doc in docs.items() if doc['collection'] == 'sections'}
    for page, soup in pages.items():
        raw = (built / page).read_text(encoding='utf-8')
        if not raw.lstrip().lower().startswith('<!doctype html>'):
            errors.append(f'{page}: нет HTML5 doctype')
        if soup.html is None or soup.html.get('lang') != 'ru':
            errors.append(f'{page}: нет html lang=ru')
        if not soup.select_one('meta[charset="utf-8" i]'):
            errors.append(f'{page}: нет charset=UTF-8')
        for tag in soup.find_all(True):
            if tag.name in LEGACY_TAGS or ':' in tag.name:
                errors.append(f'{page}: устаревший тег {tag.name}')
            for attr in tag.attrs:
                svg_dimension = attr.lower() in ('width', 'height') and (tag.name == 'svg' or tag.find_parent('svg'))
                if (attr.lower() in LEGACY_ATTRS and not svg_dimension) or attr.lower().startswith(('on', 'mso-')):
                    errors.append(f'{page}: запрещённый атрибут {attr}')
        if WORD.search(raw) or soup.find('style'):
            errors.append(f'{page}: разметка оформления Word/Joomla')
        if '{{' in raw or '{%' in raw:
            errors.append(f'{page}: неотрендеренный Liquid')
        h1s = soup.find_all('h1')
        if len(h1s) != 1 or not normalize(h1s[0].get_text()):
            errors.append(f'{page}: должен быть один непустой h1')
        title = normalize(soup.title.get_text()) if soup.title else ''
        description_tags = soup.select('meta[name="description"]')
        description = normalize(description_tags[0].get('content', '')) if len(description_tags) == 1 else ''
        for label, value, seen in (('title', title, titles), ('description', description, descriptions)):
            if not value:
                errors.append(f'{page}: пустой или неоднозначный {label}')
            elif value in seen:
                errors.append(f'{page}: повторяющийся {label} с {seen[value]}')
            else:
                seen[value] = page
        expected_url = site_url + canonical_path(page)
        canonical_tags = soup.select('link[rel="canonical"]')
        if len(canonical_tags) != 1 or canonical_tags[0].get('href') != expected_url:
            errors.append(f'{page}: canonical должен быть {expected_url}')
        for meta in soup.find_all('meta'):
            if (meta.get('name') or '').lower() in ('robots', 'googlebot', 'bingbot') and re.search(r'\b(noindex|none)\b', meta.get('content', ''), re.I):
                errors.append(f'{page}: запрещён noindex')
        for script in soup.select('script:not([type="application/ld+json"])'):
            if script.get('src') != baseurl + '/assets/site.js' or script.get_text().strip() or not script.has_attr('defer') or not exact_file(built, 'assets/site.js'):
                errors.append(f'{page}: разрешён только локальный assets/site.js с defer')
        headers, footers = soup.select('header.site'), soup.select('footer.site')
        if len(headers) != 1 or len(footers) != 1:
            errors.append(f'{page}: должен быть один header.site и footer.site')
        else:
            nav = headers[0].select_one('nav.main')
            got = [(a.get('href'), normalize(a.get_text()), a.get('aria-current') == 'page') for a in nav.find_all('a')] if nav else []
            expected = [(baseurl + item['url'], item['title'], item['url'] == canonical_path(page)) for item in nav_items]
            if got != expected:
                errors.append(f'{page}: меню не соответствует navigation.yml')
            header_copy = BeautifulSoup(str(headers[0]), 'html.parser')
            for node in header_copy.select('nav.main'):
                node.decompose()
            header_signatures.add(repr(signature(header_copy)))
            footer_signatures.add(repr(signature(footers[0])))
        alpha = soup.select('ul.letter-nav')
        requires_alpha = page == 'contents/index.html' or (page in docs and docs[page]['collection'] == 'sections')
        if len(alpha) != int(requires_alpha):
            errors.append(f'{page}: неверное число алфавитных указателей')
        if alpha:
            lis = alpha[0].find_all('li', recursive=False)
            if len(lis) != len(alphabet):
                errors.append(f'{page}: алфавит не соответствует alphabet.yml')
            for li, letter in zip(lis, alphabet):
                link = li.find('a')
                if letter in active_letters:
                    target = baseurl + canonical_path(active_letters[letter])
                    label = link.select_one('.letter-label') if link else None
                    if link is None or link.get('href') != target or normalize((label or link).get_text()) != letter or (link.get('aria-current') == 'page') != (page == active_letters[letter]):
                        errors.append(f'{page}: неверная ссылка буквы {letter}')
                elif link or not li.find('span', class_='off') or normalize((li.select_one('.letter-label') or li).get_text()) != letter:
                    errors.append(f'{page}: неверная неактивная буква {letter}')
        for node, attr in [(n, 'href') for n in soup.find_all('a')] + [(n, 'src') for n in soup.find_all('img')] + [(n, 'href') for n in soup.select('link[rel="stylesheet"]')]:
            href = node.get(attr) or ''
            try:
                target = local_target(page, href)
                if node.name == 'img' and (not target or not href or not normalize(node.get('alt', ''))):
                    raise ValueError(f'изображение должно иметь локальный src и непустой alt: {href}')
                if target is None:
                    continue
                rel, fragment = target
                if not exact_file(built, rel):
                    raise ValueError(f'файл не найден с точным регистром: {href}')
                if node.name == 'a' and rel in pages:
                    graph[page].add(rel)
                if fragment:
                    target_soup = pages.get(rel)
                    if target_soup is None or not (target_soup.find(id=fragment) or target_soup.find('a', attrs={'name': fragment})):
                        raise ValueError(f'несуществующий якорь: {href}')
            except ValueError as exc:
                errors.append(f'{page}: {exc}')
        doc = docs.get(page)
        if not doc:
            continue
        if doc['collection'] == 'sections':
            expected_members = {path for path, item in docs.items() if item['collection'] == 'exhibitions' and item['fm']['letter'] == doc['fm']['letter']}
            members = []
            main = soup.find('main')
            for anchor in main.find_all('a') if main else []:
                try:
                    target = local_target(page, anchor.get('href') or '')
                except ValueError:
                    continue  # The link checker above reports malformed URLs.
                if target and target[0] in docs and docs[target[0]]['collection'] == 'exhibitions':
                    members.append(target[0])
            if set(members) != expected_members:
                errors.append(f'{page}: состав выставок раздела не соответствует letter в исходниках')
        if doc['collection'] == 'exhibitions':
            section_path = active_letters.get(doc['fm']['letter'])
            section_url = baseurl + canonical_path(section_path) if section_path else None
            if not section_url or not any(anchor.get('href') == section_url for anchor in soup.select('nav.crumbs a')):
                errors.append(f'{page}: нет хлебной крошки текущего буквенного раздела')
        if doc['fm'].get('title') and (len(h1s) != 1 or normalize(h1s[0].get_text()) != normalize(doc['fm']['title'])):
            errors.append(f'{page}: h1 не соответствует текущему исходнику')
        compare_content = doc['collection'] == 'exhibitions' or page in ('index.html', 'conclusion/index.html') or (doc['collection'] == 'sections' and doc['body'].strip())
        if compare_content:
            try:
                expected_body = BeautifulSoup(render_content(doc['body'], baseurl), 'html.parser')
                expected_events = signature(expected_body)
                if doc['collection'] == 'exhibitions' or page == 'conclusion/index.html':
                    article = soup.find('article')
                    if article is None:
                        raise ValueError('нет article')
                    actual = BeautifulSoup(str(article), 'html.parser').article
                    actual = actual.select_one('[data-article-content]') or actual
                    for node in actual.select('h1, nav.pager'):
                        node.decompose()
                    if signature(actual) != expected_events:
                        raise ValueError('содержимое отличается от исходника: текст, структура, ссылки, подписи или порядок иллюстраций')
                else:
                    main = soup.find('main')
                    actual_events = signature(main) if main else []
                    if not expected_events or not any(actual_events[i:i + len(expected_events)] == expected_events for i in range(len(actual_events) - len(expected_events) + 1)):
                        label = 'содержимое раздела' if doc['collection'] == 'sections' else 'введение'
                        raise ValueError(f'{label} отличается от исходника: текст, структура или порядок элементов')
                report['texts_checked'] += 1
                report['images_checked'] += len(expected_body.find_all('img'))
            except ValueError as exc:
                errors.append(f'{page}: {exc}')
        if doc['collection'] == 'exhibitions':
            nodes = soup.select('script[type="application/ld+json"]')
            try:
                if len(nodes) != 1:
                    raise ValueError('должен быть один JSON-LD Article')
                data = json.loads(nodes[0].string or nodes[0].get_text())
                if not isinstance(data, dict) or data.get('@context') != 'https://schema.org' or data.get('@type') != 'Article' or data.get('headline') != doc['fm']['title'] or data.get('inLanguage') != 'ru' or data.get('mainEntityOfPage') != expected_url:
                    raise ValueError('неверные поля JSON-LD Article')
                website = data.get('isPartOf', {})
                if website.get('@type') != 'WebSite' or website.get('url') != site_url + '/' or not website.get('name'):
                    raise ValueError('неверный isPartOf JSON-LD')
            except (ValueError, TypeError, AttributeError) as exc:
                errors.append(f'{page}: {exc}')
    if len(header_signatures) > 1 or len(footer_signatures) > 1:
        errors.append('общая шапка или подвал различаются между страницами')
    try:
        tree = ET.parse(built / 'sitemap.xml')
        ns = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
        if tree.getroot().tag != ns + 'urlset':
            raise ValueError('неверный корневой элемент sitemap')
        locations = [node.text or '' for node in tree.findall(f'{ns}url/{ns}loc')]
        report['sitemap_urls'] = len(locations)
        expected = {site_url + canonical_path(page) for page in docs if page != '404.html'}
        if set(locations) != expected or len(locations) != len(set(locations)):
            errors.append(f'sitemap: множество адресов отличается; отсутствует {sorted(expected - set(locations))[:5]}, лишние {sorted(set(locations) - expected)[:5]}, дубликатов {len(locations) - len(set(locations))}')
    except (OSError, ET.ParseError, ValueError) as exc:
        errors.append(f'sitemap: {exc}')
    try:
        robots = (built / 'robots.txt').read_text()
        if f'Sitemap: {site_url}/sitemap.xml' not in robots:
            errors.append('robots.txt: неверный адрес sitemap')
        if re.search(r'^\s*Disallow\s*:\s*/', robots, re.M | re.I):
            errors.append('robots.txt: запрет индексирования страниц')
    except OSError as exc:
        errors.append(f'robots.txt: {exc}')
    reached, pending = set(), ['index.html']
    while pending:
        current = pending.pop()
        if current in reached or current not in graph:
            continue
        reached.add(current)
        pending.extend(graph[current] - reached)
    report['reachable_pages'] = len(reached)
    for page in sorted(set(docs) - reached - {'404.html'}):
        errors.append(f'{page}: страница недоступна по внутренним ссылкам')
    return report


def file_hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(root).rglob('*') if p.is_file()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=REPO / 'site')
    parser.add_argument('--site', type=Path, default=REPO / '_site')
    parser.add_argument('--report', type=Path, default=REPO / 'reports/verify_site.json')
    parser.add_argument('--repeat', action='store_true')
    parser.add_argument('--build-cmd', default='')
    args = parser.parse_args(argv)
    try:
        report = verify(args.source, args.site)
        if args.repeat:
            before = file_hashes(args.site)
            command = shlex.split(args.build_cmd) if args.build_cmd else ['bundle', 'exec', 'jekyll', 'build', '--source', str(args.source.resolve()), '--destination', str(args.site.resolve()), '--strict_front_matter']
            env = os.environ.copy()
            env['BUNDLE_GEMFILE'] = str(args.source.resolve() / 'Gemfile')
            result = subprocess.run(command, capture_output=True, text=True, env=env)
            if result.returncode:
                report['errors'].append(f'повторная сборка завершилась с кодом {result.returncode}: {result.stderr[-2000:]}')
            elif before != file_hashes(args.site):
                report['errors'].append('повторная сборка изменила файлы')
            # A repeat command is not trusted to preserve previously verified output.
            after_report = verify(args.source, args.site)
            report['errors'].extend(error for error in after_report['errors'] if error not in report['errors'])
    except (OSError, ValueError, yaml.YAMLError) as exc:
        report = {'errors': [str(exc)], 'warnings': []}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"страниц: {report.get('html_pages', 0)}, выставок: {report.get('exhibitions', 0)}, текстов сверено: {report.get('texts_checked', 0)}, изображений: {report.get('images_checked', 0)}, sitemap: {report.get('sitemap_urls', 0)}")
    print(f"ошибок: {len(report['errors'])}")
    for error in report['errors'][:30]:
        print('  ОШИБКА:', error)
    return int(bool(report['errors']))


if __name__ == '__main__':
    sys.exit(main())
