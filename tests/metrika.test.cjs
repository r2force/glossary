const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const template = fs.readFileSync(path.join(__dirname, '../site/_includes/yandex-metrika.html'), 'utf8');
const code = template.match(/<script>([\s\S]*?)<\/script>/)[1].replaceAll('{{ site.yandex_metrika_id }}', '110935159');

function run(scripts = []) {
  const inserted = [];
  const first = { parentNode: { insertBefore(script) { inserted.push(script); } } };
  const document = {
    scripts,
    referrer: 'https://yandex.ru/',
    createElement: (tag) => ({ tagName: tag }),
    getElementsByTagName: () => [first],
  };
  const window = {};
  const context = vm.createContext({ window, document, location: { href: 'https://glossary.ufacsdb.ru/contents/' }, Date });
  // In a browser, globals declared on window are available as global properties.
  Object.defineProperty(context, 'ym', { get: () => window.ym });
  vm.runInContext(code, context);
  return { inserted, calls: Array.from(window.ym.a, (args) => Array.from(args)) };
}

test('Metrika loads asynchronously and queues the supplied counter settings', () => {
  const { inserted, calls } = run();
  assert.equal(inserted.length, 1);
  assert.equal(inserted[0].async, 1);
  assert.equal(inserted[0].src, 'https://mc.yandex.ru/metrika/tag.js?id=110935159');
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], 110935159);
  assert.equal(calls[0][1], 'init');
  const options = calls[0][2];
  for (const key of ['ssr', 'clickmap', 'accurateTrackBounce', 'trackLinks']) assert.equal(options[key], true);
  assert.equal(options.webvisor, undefined);
  assert.equal(options.url, 'https://glossary.ufacsdb.ru/contents/');
  assert.equal(options.referrer, 'https://yandex.ru/');
});

test('Metrika does not inject a second copy of an already loaded tag', () => {
  const { inserted } = run([{ src: 'https://mc.yandex.ru/metrika/tag.js?id=110935159' }]);
  assert.equal(inserted.length, 0);
});
