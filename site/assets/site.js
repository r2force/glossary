'use strict';

// Alphabet links remain ordinary links. Hover never opens a preview or follows a link.
document.querySelectorAll('[data-alphabet]').forEach((panel) => {
  const letters = [...panel.querySelectorAll('.letter-nav > li')];
  panel.querySelectorAll('[data-alphabet-mode]').forEach((button) => {
    button.addEventListener('click', () => {
      panel.dataset.mode = button.dataset.alphabetMode;
      letters.forEach((letter) => letter.style.removeProperty('transform'));
      panel.querySelectorAll('[data-alphabet-mode]').forEach((mode) => {
        mode.setAttribute('aria-pressed', String(mode === button));
      });
    });
  });
  const toggle = panel.querySelector('[data-toggle-inactive]');
  toggle.addEventListener('click', () => {
    const hide = toggle.getAttribute('aria-pressed') !== 'true';
    toggle.setAttribute('aria-pressed', String(hide));
    letters.filter((letter) => letter.classList.contains('inactive-letter')).forEach((letter) => { letter.hidden = hide; });
    const activeCount = letters.filter((letter) => !letter.classList.contains('inactive-letter')).length;
    toggle.querySelector('span').textContent = hide ? `Только ${activeCount} активных` : `Все ${letters.length} буквы`;
  });
  const dock = panel.querySelector('.letter-nav');
  dock.addEventListener('pointermove', (event) => {
    if (panel.dataset.mode !== 'magnetic' || event.pointerType === 'touch') return;
    letters.forEach((letter) => {
      const rect = letter.getBoundingClientRect();
      const distance = Math.abs(event.clientX - rect.left - rect.width / 2);
      const strength = distance < 135 ? (1 + Math.cos(Math.PI * distance / 135)) / 2 : 0;
      letter.style.transform = `translateY(${-strength * 9}px) scale(${1 + strength * .36})`;
    });
  });
  dock.addEventListener('pointerleave', () => letters.forEach((letter) => letter.style.removeProperty('transform')));
});

const dialog = document.querySelector('.search-dialog');
const searchInput = document.querySelector('#search-input');
let results = [];
let indexPromise;
const loadSearch = () => {
  if (!indexPromise) indexPromise = fetch(dialog.dataset.searchIndex).then((response) => {
    if (!response.ok) throw new Error('Search index unavailable');
    return response.json();
  }).then((items) => {
    const fragment = document.createDocumentFragment();
    results = items.map((item) => {
      const result = document.createElement('li');
      result.dataset.searchText = `${item.title} ${item.text}`;
      const link = document.createElement('a');
      link.href = item.url;
      link.textContent = item.title;
      const section = document.createElement('span');
      section.textContent = `Раздел «${item.letter}» ↗`;
      link.append(section);
      result.append(link);
      fragment.append(result);
      return result;
    });
    document.querySelector('.search-results').append(fragment);
  }).catch((error) => { indexPromise = undefined; throw error; });
  return indexPromise;
};
const normalize = (text) => text.toLocaleLowerCase('ru').replaceAll('ё', 'е');
const filterSearch = () => {
  const words = normalize(searchInput.value.trim()).split(/\s+/).filter(Boolean);
  let count = 0;
  results.forEach((result) => {
    const visible = words.every((word) => normalize(result.dataset.searchText).includes(word));
    result.hidden = !visible;
    if (visible) count++;
  });
  document.querySelector('.search-status').textContent = count ? `Найдено: ${count}` : 'Ничего не найдено. Попробуйте другой запрос.';
};
const openSearch = async () => {
  dialog.showModal();
  searchInput.focus();
  document.querySelector('.search-status').textContent = 'Загрузка…';
  try { await loadSearch(); filterSearch(); }
  catch { document.querySelector('.search-status').textContent = 'Не удалось загрузить поиск. Закройте и откройте его ещё раз.'; }
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
  const result = results[Math.floor(Math.random() * results.length)];
  if (result) window.location.assign(result.querySelector('a').href);
});
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
