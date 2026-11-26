'use strict';

// Search helpers are also exercised by the dependency-free Node test suite.
const normalizeSearch = (text) => text.toLocaleLowerCase('ru').replaceAll('ё', 'е');
const queryWords = (query) => [...new Set(normalizeSearch(query.trim()).split(/\s+/).filter(Boolean))];
const matchRanges = (text, words) => {
  const normalized = normalizeSearch(text);
  const ranges = [];
  words.forEach((word) => {
    let start = normalized.indexOf(word);
    while (start !== -1) {
      ranges.push([start, start + word.length]);
      start = normalized.indexOf(word, start + 1);
    }
  });
  ranges.sort((a, b) => a[0] - b[0] || b[1] - a[1]);
  return ranges.reduce((merged, range) => {
    const previous = merged[merged.length - 1];
    if (previous && range[0] <= previous[1]) previous[1] = Math.max(previous[1], range[1]);
    else merged.push([...range]);
    return merged;
  }, []);
};
const searchDocuments = (items, query) => {
  const words = queryWords(query);
  if (!words.length) return [];
  return items.filter((item) => {
    const text = normalizeSearch(`${item.title} ${item.text}`);
    return words.every((word) => text.includes(word));
  }).map((item) => {
    const title = normalizeSearch(item.title);
    const score = words.reduce((total, word) => total + (title.includes(word) ? 1 : 0), 0);
    return {item, score};
  }).sort((a, b) => b.score - a.score).map(({item}) => item);
};
const searchExcerpt = (text, words, length = 240) => {
  const first = matchRanges(text, words)[0];
  let start = first ? Math.max(0, first[0] - 70) : 0;
  // Start at a word boundary, keeping the first matched word in view.
  if (start > 0) {
    const space = text.indexOf(' ', start);
    if (space !== -1 && space < first[0]) start = space + 1;
  }
  let end = Math.min(text.length, start + length);
  if (end < text.length) {
    const space = text.lastIndexOf(' ', end);
    if (space > start + length / 2) end = space;
  }
  return `${start > 0 ? '…' : ''}${text.slice(start, end)}${end < text.length ? '…' : ''}`;
};
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {queryWords, matchRanges, searchDocuments, searchExcerpt};
}

if (typeof document !== 'undefined') {

// Alphabet links remain ordinary links. Hover never opens a preview or follows a link.
document.querySelectorAll('[data-alphabet]').forEach((panel) => {
  const letters = [...panel.querySelectorAll('.letter-nav > li')];
  const toggle = panel.querySelector('[data-toggle-inactive]');
  toggle.addEventListener('click', () => {
    const hide = toggle.getAttribute('aria-pressed') !== 'true';
    toggle.setAttribute('aria-pressed', String(hide));
    letters.filter((letter) => letter.classList.contains('inactive-letter')).forEach((letter) => { letter.hidden = hide; });
    const activeCount = letters.filter((letter) => !letter.classList.contains('inactive-letter')).length;
    toggle.querySelector('span').textContent = hide ? `Только ${activeCount} активных` : `Все ${letters.length} буквы`;
  });
});

const dialog = document.querySelector('.search-dialog');
const searchInput = document.querySelector('#search-input');
const searchResults = document.querySelector('.search-results');
const searchStatus = document.querySelector('.search-status');
let searchItems = [];
let indexPromise;
let searchReady = false;
const loadSearch = () => {
  if (!indexPromise) indexPromise = fetch(dialog.dataset.searchIndex).then((response) => {
    if (!response.ok) throw new Error('Search index unavailable');
    return response.json();
  }).then((items) => {
    const decoder = new DOMParser();
    searchItems = items.map((item) => ({
      ...item,
      title: decoder.parseFromString(item.title, 'text/html').documentElement.textContent,
      text: decoder.parseFromString(item.text, 'text/html').documentElement.textContent,
    }));
    searchReady = true;
  }).catch((error) => { indexPromise = undefined; throw error; });
  return indexPromise;
};
const appendHighlighted = (element, text, words) => {
  let cursor = 0;
  matchRanges(text, words).forEach(([start, end]) => {
    element.append(document.createTextNode(text.slice(cursor, start)));
    const mark = document.createElement('mark');
    mark.textContent = text.slice(start, end);
    element.append(mark);
    cursor = end;
  });
  element.append(document.createTextNode(text.slice(cursor)));
};
const filterSearch = () => {
  const query = searchInput.value.trim();
  const words = queryWords(query);
  searchResults.replaceChildren();
  if (!searchReady) {
    searchStatus.textContent = 'Загрузка…';
    return;
  }
  if (!words.length) {
    searchStatus.textContent = 'Введите слово или несколько слов — поиск работает по всем статьям сайта.';
    return;
  }
  const matches = searchDocuments(searchItems, query);
  searchStatus.textContent = matches.length ? `Найдено статей: ${matches.length}` : 'Ничего не найдено. Попробуйте другой запрос.';
  const fragment = document.createDocumentFragment();
  matches.forEach((item) => {
    const result = document.createElement('li');
    const link = document.createElement('a');
    const url = new URL(item.url, window.location.origin);
    url.searchParams.set('q', query);
    link.href = url.pathname + url.search;
    const heading = document.createElement('div');
    heading.className = 'search-result-heading';
    const title = document.createElement('span');
    title.className = 'search-result-title';
    appendHighlighted(title, item.title, words);
    const section = document.createElement('span');
    section.className = 'search-result-section';
    section.textContent = item.letter ? `Раздел «${item.letter}» ↗` : 'Статья ↗';
    heading.append(title, section);
    const excerpt = document.createElement('p');
    excerpt.className = 'search-result-excerpt';
    appendHighlighted(excerpt, searchExcerpt(item.text, words), words);
    link.append(heading, excerpt);
    result.append(link);
    fragment.append(result);
  });
  searchResults.append(fragment);
};
const openSearch = async () => {
  dialog.showModal();
  searchInput.focus();
  searchStatus.textContent = 'Загрузка…';
  try { await loadSearch(); filterSearch(); }
  catch { searchStatus.textContent = 'Не удалось загрузить поиск. Закройте и откройте его ещё раз.'; }
};
document.querySelector('[data-open-search]').addEventListener('click', openSearch);
document.querySelector('[data-close-search]').addEventListener('click', () => dialog.close());
searchInput.addEventListener('input', filterSearch);
dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });
document.addEventListener('keydown', (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault();
    if (dialog.open) dialog.close(); else openSearch();
  }
});
document.querySelector('[data-random-exhibition]').addEventListener('click', async () => {
  try { await loadSearch(); } catch { openSearch(); return; }
  const exhibitions = searchItems.filter((item) => item.letter);
  const item = exhibitions[Math.floor(Math.random() * exhibitions.length)];
  if (item) window.location.assign(item.url);
});

// Preserve the author's markup while highlighting a query opened from search.
const pageQuery = new URLSearchParams(window.location.search).get('q');
if (pageQuery) {
  searchInput.value = pageQuery;
  const words = queryWords(pageQuery);
  document.querySelectorAll('main h1, main [data-article-content], main .introduction-copy').forEach((root) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: (node) => node.parentElement.closest('script, style, svg, mark, button') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT,
    });
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((node) => {
      if (!matchRanges(node.textContent, words).length) return;
      const fragment = document.createDocumentFragment();
      appendHighlighted(fragment, node.textContent, words);
      node.replaceWith(fragment);
    });
  });
  const firstMatch = document.querySelector('main mark');
  if (firstMatch) requestAnimationFrame(() => firstMatch.scrollIntoView({block: 'center'}));
}
const cite = document.querySelector('[data-copy-citation]');
if (cite) cite.addEventListener('click', async () => {
  const text = `${document.querySelector('h1').textContent} — ${document.querySelector('[data-article-content]').textContent.trim()} («Книга – Выставка – Читатель», ЦГДБ г. Уфы) ${window.location.href}`;
  try {
    await navigator.clipboard.writeText(text);
    cite.textContent = 'Цитата скопирована';
  } catch {
    cite.textContent = 'Не удалось скопировать';
  }
  setTimeout(() => { cite.textContent = 'Цитировать'; }, 2000);
});

}
