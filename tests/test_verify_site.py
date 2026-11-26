"""Regression checks for publication defects the previous verifier accepted.

The fixture is a small, complete site built as plain HTML; tests need no Ruby,
network, external archives, or artifacts from this checkout.
"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import sys
import shlex
import unittest

import yaml
from bs4 import BeautifulSoup

SPEC = importlib.util.spec_from_file_location('verify_site', Path(__file__).resolve().parents[1] / 'scripts/verify_site.py')
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


class SiteVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.built = self.root / 'site', self.root / 'built'
        self.config = {
            'url': 'https://example.test', 'baseurl': '/glossary',
            'collections': {'exhibitions': {'permalink': '/exhibitions/:name/'}, 'sections': {'permalink': '/sections/:name/'}},
        }
        self.nav = [{'title': 'Home', 'url': '/'}, {'title': 'Contents', 'url': '/contents/'}, {'title': 'Conclusion', 'url': '/conclusion/'}]
        self.write(self.source, '_config.yml', yaml.safe_dump(self.config))
        self.write(self.source, '_data/navigation.yml', yaml.safe_dump(self.nav))
        self.write(self.source, '_data/alphabet.yml', yaml.safe_dump(['А', 'Б']))
        for name in ('default', 'home', 'article', 'section', 'exhibition'):
            self.write(self.source, f'_layouts/{name}.html', '{{ content }}')
        for name in ('head', 'header', 'nav', 'footer', 'breadcrumbs', 'letter-nav', 'cards', 'pager'):
            value = '{% include nav.html %}' if name == 'header' else '{{ site.data.navigation }}' if name == 'nav' else ''
            self.write(self.source, f'_includes/{name}.html', value)
        for root in (self.source, self.built):
            self.write(root, 'assets/site.css', 'body { color: black; }')
        self.doc('index.html', {'layout': 'home'}, '<p>Introduction.</p>')
        self.doc('contents/index.html', {'title': 'Contents'}, '{% include letter-nav.html %}')
        self.doc('conclusion/index.html', {'title': 'Conclusion'}, '<p>Conclusion body.</p>')
        self.doc('404.html', {'title': 'Missing'}, '{{ page.title }}')
        self.doc('_sections/a.html', {'title': 'Section A', 'letter': 'А', 'order': 1}, '')
        gallery = '''<p>Before.</p><figure><a href="{{ '/images/One.png' | relative_url }}"><img src="{{ '/images/thumbs/One.png' | relative_url }}" alt="First"></a><figcaption>First caption.</figcaption></figure><p>Between.</p><figure><a href="{{ '/images/Two.png' | relative_url }}"><img src="{{ '/images/thumbs/Two.png' | relative_url }}" alt="Second"></a><figcaption>Second caption.</figcaption></figure><p>After.</p><ul><li>One</li><li>Two</li></ul>'''
        self.doc('_exhibitions/first.html', {'title': 'First', 'letter': 'А', 'order': 1}, gallery)
        self.doc('_exhibitions/second.html', {'title': 'Second', 'letter': 'А', 'order': 2}, '<p>Second body.</p>')
        self.pages = {
            'index.html': ('Home', '<p>Introduction.</p>'),
            'contents/index.html': ('Contents', '<p>Contents body.</p>'),
            'conclusion/index.html': ('Conclusion', '<article><h1>Conclusion</h1><p>Conclusion body.</p></article>'),
            '404.html': ('Missing', '<p>Missing.</p>'),
            'sections/a/index.html': ('Section A', '<p>Section body.</p>'),
            'exhibitions/first/index.html': ('First', '<article><h1>First</h1>' + verifier.render_content(gallery, '/glossary') + '<nav class="pager"></nav></article>'),
            'exhibitions/second/index.html': ('Second', '<article><h1>Second</h1><p>Second body.</p><nav class="pager"></nav></article>'),
        }
        for path, (title, body) in self.pages.items():
            self.write(self.built, path, self.page(path, title, body))
        for path in ('images/One.png', 'images/Two.png', 'images/thumbs/One.png', 'images/thumbs/Two.png'):
            self.write(self.built, path, 'media checked by verify_media.py')
        self.sitemap()
        for root in (self.source, self.built):
            self.write(root, 'robots.txt', 'User-agent: *\nAllow: /\nSitemap: https://example.test/glossary/sitemap.xml\n')
        self.write(self.source, 'sitemap.xml', '---\nlayout: none\n---\n<urlset/>')

    def write(self, root, path, body):
        full = root / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(body, encoding='utf-8')

    def doc(self, path, metadata, body):
        self.write(self.source, path, '---\n' + yaml.safe_dump(metadata, allow_unicode=True) + '---\n' + body)

    def page(self, path, title, body):
        url = verifier.canonical_path(path)
        canonical = 'https://example.test/glossary' + url
        nav = '<nav class="main">' + ''.join(f'<a href="/glossary{item["url"]}"' + (' aria-current="page"' if item['url'] == url else '') + f'>{item["title"]}</a>' for item in self.nav) + '</nav>'
        alpha = ''
        if path in ('contents/index.html', 'sections/a/index.html'):
            alpha = '<ul class="letter-nav"><li><a href="/glossary/sections/a/"' + (' aria-current="page"' if path == 'sections/a/index.html' else '') + '>А</a></li><li><span class="off">Б</span></li></ul>'
        heading = '' if '<h1>' in body else f'<h1>{title}</h1>'
        links = ''.join(f'<a href="/glossary{verifier.canonical_path(p)}">Open</a>' for p in self.pages if p != '404.html')
        if path == 'sections/a/index.html':
            body += ''.join(f'<a href="/glossary/{p}">Exhibition</a>' for p in self.pages if p.startswith('exhibitions/'))
        if path.startswith('exhibitions/'):
            body = '<nav class="crumbs"><a href="/glossary/sections/a/">Section A</a></nav>' + body
        ld = ''
        if path.startswith('exhibitions/'):
            data = {'@context': 'https://schema.org', '@type': 'Article', 'headline': title, 'inLanguage': 'ru', 'mainEntityOfPage': canonical, 'isPartOf': {'@type': 'WebSite', 'name': 'Glossary', 'url': 'https://example.test/glossary/'}}
            ld = '<script type="application/ld+json">' + json.dumps(data) + '</script>'
        return f'<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><title>{title}</title><meta name="description" content="Description for {title}"><link rel="canonical" href="{canonical}"><link rel="stylesheet" href="/glossary/assets/site.css">{ld}</head><body><a href="#content">Skip</a><header class="site"><p>Glossary</p>{nav}</header><main id="content">{heading}{alpha}{body}</main>{links}<footer class="site">Footer</footer></body></html>'

    def sitemap(self):
        urls = [f'https://example.test/glossary{verifier.canonical_path(p)}' for p in self.pages if p != '404.html']
        self.write(self.built, 'sitemap.xml', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join('<url><loc>' + url + '</loc></url>' for url in urls) + '</urlset>')

    def errors(self):
        return verifier.verify(self.source, self.built)['errors']

    def mutate(self, path, change):
        p = self.built / path
        soup = BeautifulSoup(p.read_text(), 'html.parser')
        change(soup)
        p.write_text(str(soup))

    def assert_error(self, needle):
        errors = self.errors()
        self.assertTrue(any(needle in error for error in errors), errors)

    def test_current_source_is_baseline_without_fixed_counts(self):
        report = verifier.verify(self.source, self.built)
        self.assertEqual([], report['errors'])
        self.assertEqual(2, report['exhibitions'])
        self.assertEqual(4, report['texts_checked'])

    def test_swapped_image_sources_fail(self):
        def swap(soup):
            a, b = soup.select('article img')
            a['src'], b['src'] = b['src'], a['src']
        self.mutate('exhibitions/first/index.html', swap)
        self.assert_error('содержимое отличается')

    def test_changed_gallery_original_fails(self):
        self.mutate('exhibitions/first/index.html', lambda soup: soup.select_one('article figure a').__setitem__('href', '/glossary/images/Two.png'))
        self.assert_error('содержимое отличается')

    def test_caption_and_image_position_are_preserved(self):
        self.mutate('exhibitions/first/index.html', lambda soup: soup.select_one('figcaption').decompose())
        self.assert_error('содержимое отличается')

    def test_image_cannot_move_past_text(self):
        def move(soup):
            figure = soup.select_one('article figure').extract()
            soup.select('article p')[-1].insert_after(figure)
        self.mutate('exhibitions/first/index.html', move)
        self.assert_error('содержимое отличается')

    def test_list_structure_cannot_be_flattened(self):
        def flatten(soup):
            for li in soup.select('article li'):
                li.name = 'p'
            soup.select_one('article ul').unwrap()
        self.mutate('exhibitions/first/index.html', flatten)
        self.assert_error('содержимое отличается')

    def test_empty_sitemap_fails(self):
        self.write(self.built, 'sitemap.xml', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>')
        self.assert_error('sitemap: множество адресов отличается')

    def test_duplicate_sitemap_url_fails(self):
        path = self.built / 'sitemap.xml'
        path.write_text(path.read_text().replace('</urlset>', '<url><loc>https://example.test/glossary/</loc></url></urlset>'))
        self.assert_error('дубликатов 1')

    def test_local_and_cross_page_absolute_anchors_fail(self):
        for href in ('#missing', '/glossary/contents/#missing', 'https://example.test/glossary/contents/#missing'):
            with self.subTest(href=href):
                original = (self.built / 'index.html').read_text()
                self.write(self.built, 'index.html', original.replace('</main>', f'<a href="{href}">bad</a></main>'))
                self.assert_error('несуществующий якорь')
                self.write(self.built, 'index.html', original)

    def test_real_cross_page_anchor_passes(self):
        p = self.built / 'index.html'
        p.write_text(p.read_text().replace('</main>', '<a href="https://example.test/glossary/contents/#content">good</a></main>'))
        self.assertEqual([], self.errors())

    def test_directory_case_mismatch_fails(self):
        p = self.built / 'index.html'
        p.write_text(p.read_text().replace('/glossary/assets/site.css', '/glossary/Assets/site.css'))
        self.assert_error('точным регистром')

    def test_wrong_canonical_fails(self):
        self.mutate('index.html', lambda soup: soup.select_one('link[rel="canonical"]').__setitem__('href', 'https://wrong.test/'))
        self.assert_error('canonical должен быть')

    def test_duplicate_description_fails(self):
        self.mutate('index.html', lambda soup: soup.select_one('meta[name="description"]').__setitem__('content', 'Description for Contents'))
        self.assert_error('повторяющийся description')

    def test_invalid_json_ld_fails(self):
        def change(soup):
            tag = soup.select_one('script[type="application/ld+json"]')
            data = json.loads(tag.string)
            data['mainEntityOfPage'] = 'https://wrong.test/'
            tag.string = json.dumps(data)
        self.mutate('exhibitions/first/index.html', change)
        self.assert_error('неверные поля JSON-LD')

    def test_source_edit_is_detected_against_stale_build(self):
        p = self.source / '_exhibitions/second.html'
        p.write_text(p.read_text().replace('Second body.', 'Updated body.'))
        self.assert_error('содержимое отличается')

    def test_unknown_content_liquid_is_rejected(self):
        p = self.source / '_exhibitions/second.html'
        p.write_text(p.read_text() + '{{ site.exhibitions | jsonify }}')
        self.assert_error('поддерживается только literal relative_url')

    def test_missing_section_member_fails(self):
        self.mutate('sections/a/index.html', lambda soup: soup.select_one('main a[href="/glossary/exhibitions/first/index.html"]').decompose())
        self.assert_error('состав выставок раздела')

    def test_missing_section_breadcrumb_fails(self):
        self.mutate('exhibitions/first/index.html', lambda soup: soup.select_one('nav.crumbs').decompose())
        self.assert_error('нет хлебной крошки')

    def test_section_body_is_checked_when_present(self):
        self.doc('_sections/a.html', {'title': 'Section A', 'letter': 'А', 'order': 1}, '<p>Extra section text.</p>')
        path = self.built / 'sections/a/index.html'
        old = path.read_text()
        path.write_text(old.replace('<p>Section body.</p>', '<p>Section body.</p><p>Extra section text.</p>'))
        self.assertEqual([], self.errors())
        path.write_text(old)
        self.assert_error('содержимое раздела отличается')

    def test_collection_metadata_schema(self):
        for metadata, message in (
            ({'title': 'Second', 'letter': 'А'}, 'целочисленный order'),
            ({'title': 'Second', 'letter': 'А', 'order': True}, 'целочисленный order'),
            ({'title': ['Second'], 'letter': 'А', 'order': 2}, 'непустые строки title и letter'),
            ({'title': 'Second', 'letter': '', 'order': 2}, 'непустые строки title и letter'),
        ):
            with self.subTest(metadata=metadata):
                self.doc('_exhibitions/second.html', metadata, '<p>Second body.</p>')
                self.assert_error(message)

    def test_noindex_fails_case_insensitively(self):
        p = self.built / 'index.html'
        p.write_text(p.read_text().replace('</head>', '<meta name="robots" content="NOINDEX, follow"></head>'))
        self.assert_error('запрещён noindex')

    def test_path_cannot_escape_site(self):
        self.write(self.root, 'outside.txt', 'outside')
        p = self.built / 'index.html'
        p.write_text(p.read_text().replace('</main>', '<a href="../outside.txt">bad</a></main>'))
        self.assert_error('за пределами сайта')

    def test_unsafe_link_scheme_fails(self):
        p = self.built / 'index.html'
        p.write_text(p.read_text().replace('</main>', '<a href="javascript:alert(1)">bad</a></main>'))
        self.assert_error('запрещённая схема')

    def test_local_deferred_site_script_passes(self):
        self.write(self.built, 'assets/site.js', "'use strict';")
        p = self.built / 'index.html'
        p.write_text(p.read_text().replace('</body>', '<script src="/glossary/assets/site.js" defer></script></body>'))
        self.assertEqual([], self.errors())

    def test_inline_and_external_scripts_are_rejected(self):
        p = self.built / 'index.html'
        original = p.read_text()
        for script in ('<script>alert(1)</script>', '<script src="https://example.test/script.js" defer></script>', '<script src="/glossary/assets/site.js"></script>'):
            with self.subTest(script=script):
                p.write_text(original.replace('</body>', script + '</body>'))
                self.assert_error('разрешён только локальный assets/site.js с defer')
        p.write_text(original)

    def enable_metrika(self):
        self.config['yandex_metrika_id'] = 110935159
        self.write(self.source, '_config.yml', yaml.safe_dump(self.config))
        template = (Path(__file__).resolve().parents[1] / 'site/_includes/yandex-metrika.html').read_text()
        self.write(self.source, '_includes/yandex-metrika.html', template)
        code = template.split('<script>', 1)[1].split('</script>', 1)[0].replace('{{ site.yandex_metrika_id }}', '110935159')
        markup = '<script>' + code + '</script><noscript><div><img class="metrika-pixel" src="https://mc.yandex.ru/watch/110935159" alt=""></div></noscript>'
        for path in self.pages:
            p = self.built / path
            p.write_text(p.read_text().replace('<body>', '<body>' + markup))

    def test_configured_metrika_passes(self):
        self.enable_metrika()
        self.assertEqual([], self.errors())

    def test_missing_or_duplicate_metrika_fails(self):
        self.enable_metrika()
        p = self.built / 'index.html'
        original = p.read_text()
        self.mutate('index.html', lambda soup: soup.select_one('script:not([type])').decompose())
        self.assert_error('должен быть один счётчик Метрики')
        p.write_text(original)
        script = str(BeautifulSoup(original, 'html.parser').select_one('script:not([type])'))
        p.write_text(original.replace('</body>', script + '</body>'))
        self.assert_error('должен быть один счётчик Метрики')

    def test_metrika_pixel_cannot_replace_an_article_image(self):
        self.enable_metrika()
        self.mutate('exhibitions/first/index.html', lambda soup: soup.select_one('article img').__setitem__('src', 'https://mc.yandex.ru/watch/110935159'))
        self.assert_error('изображение должно иметь локальный src')

    def test_wrong_metrika_id_is_rejected(self):
        self.enable_metrika()
        p = self.built / 'index.html'
        p.write_text(p.read_text().replace("ym(110935159, 'init'", "ym(999, 'init'"))
        self.assert_error('разрешён только локальный assets/site.js')
        self.assert_error('должен быть один счётчик Метрики')

    def test_404_can_be_excluded_from_indexing(self):
        p = self.built / '404.html'
        p.write_text(p.read_text().replace('</head>', '<meta name="robots" content="noindex, follow"></head>'))
        self.assertEqual([], self.errors())

    def test_malformed_json_ld_is_rejected_on_home(self):
        p = self.built / 'index.html'
        p.write_text(p.read_text().replace('</head>', '<script type="application/ld+json">{broken}</script></head>'))
        self.assert_error('некорректный JSON-LD')

    def test_repeat_accepts_identical_output(self):
        report = self.root / 'report.json'
        command = shlex.join([sys.executable, '-c', 'pass'])
        with contextlib.redirect_stdout(io.StringIO()):
            code = verifier.main(['--source', str(self.source), '--site', str(self.built), '--report', str(report), '--repeat', '--build-cmd', command])
        self.assertEqual(0, code, json.loads(report.read_text())['errors'])

    def test_repeat_detects_changed_output(self):
        report = self.root / 'report.json'
        command = shlex.join([sys.executable, '-c', f'from pathlib import Path; Path({str(self.built / "unexpected.txt")!r}).write_text("changed")'])
        with contextlib.redirect_stdout(io.StringIO()):
            code = verifier.main(['--source', str(self.source), '--site', str(self.built), '--report', str(report), '--repeat', '--build-cmd', command])
        self.assertEqual(1, code)
        self.assertIn('повторная сборка изменила файлы', json.loads(report.read_text())['errors'])


if __name__ == '__main__':
    unittest.main()
