const {test} = require('node:test');
const assert = require('node:assert/strict');
const {queryWords, matchRanges, searchDocuments, searchExcerpt} = require('../site/assets/site.js');

const articles = [
  {title: 'Введение', text: 'Организация выставки помогает заинтересовать ребёнка.'},
  {title: 'Выставка – театр', text: 'Читатели разыгрывают сцену по книге.'},
  {title: 'Заключение', text: 'Приглашаем коллег к соавторству.'},
];

test('full text matches a word absent from the title, including introduction and conclusion', () => {
  assert.deepEqual(searchDocuments(articles, 'ребенка').map(x => x.title), ['Введение']);
  assert.deepEqual(searchDocuments(articles, 'соавторству').map(x => x.title), ['Заключение']);
});
test('all query words must match the same article regardless of order, case and ё', () => {
  assert.equal(searchDocuments(articles, 'РЕБЁНКА организация').length, 1);
  assert.equal(searchDocuments(articles, 'ребёнка театр').length, 0);
  assert.deepEqual(queryWords('  ТЕАТР театр\n ЁЖ  '), ['театр', 'еж']);
});
test('title matches precede body-only matches', () => {
  assert.deepEqual(searchDocuments(articles, 'выставк').map(x => x.title), ['Выставка – театр', 'Введение']);
});
test('highlight ranges preserve original case and ё and merge overlapping matches', () => {
  const text = 'Ёж, ёж и театр';
  assert.deepEqual(matchRanges(text, queryWords('еж ёж театр теа')), [[0, 2], [4, 6], [9, 14]]);
  assert.deepEqual(matchRanges('абаба', ['аба']), [[0, 5]]);
});
test('special characters are searched literally without a regular expression', () => {
  const text = 'Символы [а]+ <img onerror=alert(1)>';
  assert.deepEqual(matchRanges(text, ['[а]+']), [[8, 12]]);
  assert.equal(searchDocuments([{title: text, text: ''}], '[а]+').length, 1);
  assert.equal(searchDocuments(articles, '[а]+').length, 0);
});
test('excerpt finds a match deep inside an article and keeps its original text', () => {
  const text = 'Начало статьи. '.repeat(100) + 'Необычный ТЕАТР увлекает детей. ' + 'Продолжение. '.repeat(100);
  const excerpt = searchExcerpt(text, ['театр']);
  assert.ok(excerpt.includes('ТЕАТР'));
  assert.ok(excerpt.startsWith('…') && excerpt.endsWith('…'));
  assert.ok(excerpt.length <= 242);
});
test('empty queries, no matches and short texts are handled', () => {
  assert.deepEqual(searchDocuments(articles, '  '), []);
  assert.deepEqual(searchDocuments(articles, 'несуществующееслово'), []);
  assert.deepEqual(matchRanges('Текст', []), []);
  assert.equal(searchExcerpt('Короткий текст.', ['театр']), 'Короткий текст.');
});
