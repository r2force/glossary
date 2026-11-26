import React, { useState } from 'react';
import {
  Check,
  Copy,
  Terminal,
  FileCode,
  Sparkles,
  Layers,
  BookOpen,
  Compass,
  Cpu,
  CheckCircle2,
  ArrowRight,
  FolderGit2,
} from 'lucide-react';

interface CodeStep {
  id: string;
  phase: string;
  title: string;
  filePath: string;
  language: string;
  summary: string;
  highlights: string[];
  code: string;
}

const AGENT_STEPS: CodeStep[] = [
  {
    id: 'step-1',
    phase: 'Этап 1 · Алфавитный указатель (Liquid + HTML)',
    title: 'Интерактивный алфавит с подсчётом ссылок и быстрым превью разделов',
    filePath: 'site/_includes/letter-nav.html',
    language: 'liquid / html',
    summary:
      'Заменяет плоский список из 10 строк на полноценную каталожную матрицу всех 33 букв русского алфавита (27 активных разделов со счётчиками выставок и выпадающим превью ссылок + 6 неактивных букв Ё, Й, Щ, Ъ, Ы, Ь с архивной штриховкой). Не требует плагинов Jekyll.',
    highlights: [
      'Автоматический подсчёт количества выставок через Liquid: site.exhibitions | where: "letter", letter',
      'Всплывающий поповер (.letter-popover) с прямыми ссылками на первые 5 выставок каждой буквы без перезагрузки страницы',
      'Атрибуты data-letter и data-count для подключения магнитного эффекта и тепловой шкалы из TypeScript',
    ],
    code: `{%- comment -%}
  Файл: site/_includes/letter-nav.html
  Редизайн: Интерактивная матрица русского алфавита А–Я с превью ссылок и счётчиками
{%- endcomment -%}
{%- assign full_alphabet = "А,Б,В,Г,Д,Е,Ё,Ж,З,И,Й,К,Л,М,Н,О,П,Р,С,Т,У,Ф,Х,Ц,Ч,Ш,Щ,Ъ,Ы,Ь,Э,Ю,Я" | split: "," -%}

<nav class="alphabet-bar" aria-label="Алфавитный указатель от А до Я" data-alphabet-dock>
  <div class="alphabet-bar__header">
    <div class="alphabet-bar__title">
      <span class="alphabet-bar__badge">А–Я</span>
      <span>Алфавитный указатель форм книжных выставок</span>
    </div>
    <div class="alphabet-bar__actions">
      <button type="button" class="alphabet-toggle-btn" data-toggle-empty-letters>
        Все 33 литеры
      </button>
      <button type="button" class="alphabet-search-trigger" data-open-cmdk>
        Быстрый поиск <kbd>⌘K</kbd>
      </button>
    </div>
  </div>

  <ul class="letter-nav" role="list">
    {%- for letter in full_alphabet -%}
      {%- assign sec = site.sections | where: "letter", letter | first -%}
      {%- assign items_in_letter = site.exhibitions | where: "letter", letter | sort: "order" -%}
      {%- assign count = items_in_letter.size -%}

      {%- if sec and count > 0 -%}
        <li class="letter-nav__item is-active" data-letter-item="{{ letter }}" data-count="{{ count }}">
          <a
            href="{{ sec.url | relative_url }}"
            class="letter-tile"
            data-magnetic-tile
            {% if page.letter == letter %}aria-current="page"{% endif %}
          >
            <span class="letter-tile__char">{{ letter }}</span>
            <span class="letter-tile__count">{{ count }}</span>
            <span class="letter-tile__bar" style="--fill: {{ count | times: 100 | divided_by: 34 }}%"></span>
          </a>

          <!-- Всплывающая карточка быстрых ссылок при наведении / фокусе -->
          <div class="letter-popover" role="region" aria-label="Быстрые ссылки раздела {{ letter }}">
            <div class="letter-popover__head">
              <strong>Раздел «{{ letter }}»</strong>
              <span>{{ count }} форм</span>
            </div>
            <ul class="letter-popover__links">
              {%- for ex in items_in_letter limit: 5 -%}
                <li>
                  <a href="{{ ex.url | relative_url }}">{{ ex.title | escape }}</a>
                </li>
              {%- endfor -%}
            </ul>
            <a class="letter-popover__all" href="{{ sec.url | relative_url }}">
              Все выставки на «{{ letter }}» ({{ count }}) →
            </a>
          </div>
        </li>
      {%- else -%}
        <li
          class="letter-nav__item is-disabled"
          data-empty-letter
          title="В глоссарии нет терминов на букву «{{ letter }}»"
        >
          <span class="letter-tile is-off" aria-disabled="true">
            <span class="letter-tile__char">{{ letter }}</span>
            <span class="letter-tile__count">—</span>
          </span>
        </li>
      {%- endif -%}
    {%- endfor -%}
  </ul>
</nav>`,
  },
  {
    id: 'step-2',
    phase: 'Этап 2 · Дизайнерские интерактивные эффекты (TypeScript / JS)',
    title: 'Магнитный Fisheye-док алфавита, курсор-прожектор на карточках и поиск ⌘K',
    filePath: 'site/assets/site.ts',
    language: 'typescript',
    summary:
      'Добавляет микро-взаимодействия, которые ценят современные дизайнеры: плавное масштабирование соседних букв алфавита по косинусной волне при движении мыши, радиальный прожектор (--mouse-x, --mouse-y) на каталожных карточках, клавиши ←/→ для перелистывания выставок и горячую клавишу ⌘K.',
    highlights: [
      'Proximity Fisheye Dock: вычисляет дистанцию курсора до каждой буквы и плавно приподнимает соседние литеры',
      'Radial Cursor Spotlight: передаёт координаты курсора в CSS-переменные карточки',
      'Keyboard Navigation: нажатие любой русской буквы на клавиатуре подсвечивает и скроллит к нужной секции',
    ],
    code: `/**
 * Файл: site/assets/site.ts (компилируется в site/assets/site.js)
 * Интерактивные модули для «Книга – Выставка – Читатель»
 */

// 1. Магнитный Fisheye-эффект для алфавитной панели (macOS / Raycast style)
function initMagneticAlphabetDock(): void {
  const dock = document.querySelector<HTMLElement>('[data-alphabet-dock]');
  if (!dock) return;

  const tiles = Array.from(dock.querySelectorAll<HTMLElement>('[data-magnetic-tile]'));
  const RADIUS = 130; // Радиус магнитного притяжения в пикселях

  dock.addEventListener('mousemove', (e: MouseEvent) => {
    tiles.forEach((tile) => {
      const rect = tile.getBoundingClientRect();
      const tileCenterX = rect.left + rect.width / 2;
      const tileCenterY = rect.top + rect.height / 2;
      const dist = Math.hypot(e.clientX - tileCenterX, e.clientY - tileCenterY);

      if (dist < RADIUS) {
        const wave = (1 + Math.cos((Math.PI * dist) / RADIUS)) / 2;
        const scale = 1 + wave * 0.24;
        const lift = -wave * 6;
        tile.style.transform = \`translate3d(0, \${lift.toFixed(1)}px, 0) scale(\${scale.toFixed(3)})\`;
        tile.style.zIndex = String(Math.round(wave * 10) + 2);
      } else {
        tile.style.transform = '';
        tile.style.zIndex = '';
      }
    });
  });

  dock.addEventListener('mouseleave', () => {
    tiles.forEach((tile) => {
      tile.style.transform = '';
      tile.style.zIndex = '';
    });
  });

  // Переключатель скрытия пустых букв (Ё, Й, Щ, Ъ, Ы, Ь)
  const toggleBtn = dock.querySelector<HTMLButtonElement>('[data-toggle-empty-letters]');
  toggleBtn?.addEventListener('click', () => {
    const hidden = dock.classList.toggle('hide-empty-letters');
    toggleBtn.textContent = hidden ? 'Только 27 активных' : 'Все 33 литеры';
  });
}

// 2. Радиальный прожектор на каталожных карточках (--mouse-x, --mouse-y)
function initCatalogCardSpotlight(): void {
  const cards = document.querySelectorAll<HTMLElement>('.cards > li, .catalog-card');
  cards.forEach((card) => {
    card.addEventListener('mousemove', (e: MouseEvent) => {
      const rect = card.getBoundingClientRect();
      card.style.setProperty('--mouse-x', \`\${e.clientX - rect.left}px\`);
      card.style.setProperty('--mouse-y', \`\${e.clientY - rect.top}px\`);
    });
  });
}

// 3. Навигация с клавиатуры: нажатие русской буквы или стрелок ← / →
function initKeyboardShortcuts(): void {
  window.addEventListener('keydown', (e: KeyboardEvent) => {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

    // ⌘K или / открывает модальное окно быстрого поиска
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      document.querySelector<HTMLElement>('[data-cmdk-modal]')?.classList.toggle('is-open');
      return;
    }

    // Листание соседних выставок в _layouts/exhibition.html
    if (e.key === 'ArrowLeft') {
      document.querySelector<HTMLAnchorElement>('.pager a[rel="prev"]')?.click();
    } else if (e.key === 'ArrowRight') {
      document.querySelector<HTMLAnchorElement>('.pager a[rel="next"]')?.click();
    }

    // Быстрый переход по нажатию русской буквы А–Я
    const char = e.key.toUpperCase();
    if (/^[А-ЯЁ]$/.test(char) && !e.metaKey && !e.ctrlKey && !e.altKey) {
      const target = document.querySelector<HTMLElement>(\`[data-letter-item="\${char}"] a\`);
      target?.focus();
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initMagneticAlphabetDock();
  initCatalogCardSpotlight();
  initKeyboardShortcuts();
});`,
  },
  {
    id: 'step-3',
    phase: 'Этап 3 · Архивная система стилей (CSS)',
    title: 'Полное обновление site/assets/site.css в эстетике «Библиофильский Архив»',
    filePath: 'site/assets/site.css',
    language: 'css',
    summary:
      'Заменяет базовый 53-строчный CSS на выверенную типографическую систему: палитра тёплой бумаги (#FAF6F0) и терракотового переплёта (#9E3B24), каталожные карточки с перфорацией, всплывающие поповеры для букв алфавита и адаптивная верстка.',
    highlights: [
      'Стилизация .letter-nav и всплывающего .letter-popover с плавным появлением при hover/focus-within',
      'Карточки .cards li как настоящие библиотечные формуляры с эффектом прожектора',
      'Оформление фотографий выставок в виде музейных паспарту с аккуратной подписью',
    ],
    code: `:root {
  --bg-paper: #FAF6F0;
  --bg-cream: #F3ECE2;
  --bg-card: #FFFFFF;
  --ink: #1A1817;
  --ink-secondary: #4A443F;
  --muted: #7A7167;
  --line: #E2D9CC;
  --line-strong: #C5B9A8;
  --accent: #9E3B24;
  --accent-hover: #B8462B;
  --ochre: #C88A32;
  --sage: #2E5A44;
  --font-serif: "Cormorant Garamond", "Iowan Old Style", Georgia, serif;
  --font-sans: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: "JetBrains Mono", monospace;
}

body {
  margin: 0;
  background-color: var(--bg-paper);
  background-image: radial-gradient(rgba(26, 24, 23, 0.03) 1px, transparent 0);
  background-size: 24px 24px;
  color: var(--ink);
  font: 16px/1.68 var(--font-sans);
}

.wrap {
  max-width: 74rem;
  margin: 0 auto;
  padding: 0 1.5rem;
}

/* Алфавитная матрица и поповеры с быстрыми ссылками */
.alphabet-bar {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--line);
  border-radius: 1rem;
  padding: 1.25rem;
  margin: 1.75rem 0;
  box-shadow: 0 12px 32px -16px rgba(26, 24, 23, 0.08);
  backdrop-filter: blur(10px);
}

.letter-nav {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(3.2rem, 1fr));
  gap: 0.45rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.letter-nav__item {
  position: relative;
}

.letter-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  height: 3.6rem;
  padding: 0.35rem;
  border: 1px solid var(--line);
  border-radius: 0.65rem;
  background: var(--bg-card);
  color: var(--ink);
  text-decoration: none;
  transition: transform 0.2s cubic-bezier(0.22, 1, 0.36, 1),
              border-color 0.2s ease,
              background-color 0.2s ease;
}

.letter-tile:hover,
.letter-tile:focus-visible {
  border-color: var(--accent);
  background: var(--bg-paper);
  color: var(--accent);
}

.letter-tile[aria-current="page"] {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
  box-shadow: 0 8px 18px -6px rgba(158, 59, 36, 0.45);
}

.letter-tile__char {
  font-family: var(--font-serif);
  font-size: 1.35rem;
  font-weight: 700;
  line-height: 1;
}

.letter-tile__count {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--muted);
}

.letter-tile[aria-current="page"] .letter-tile__count {
  color: rgba(255, 255, 255, 0.85);
}

.letter-tile__bar {
  width: 100%;
  height: 3px;
  background: var(--bg-cream);
  border-radius: 99px;
  overflow: hidden;
}

.letter-tile__bar::after {
  content: "";
  display: block;
  height: 100%;
  width: var(--fill, 25%);
  background: var(--accent);
}

/* Всплывающее превью ссылок при наведении на букву */
.letter-popover {
  position: absolute;
  top: calc(100% + 0.5rem);
  left: 50%;
  transform: translateX(-50%) translateY(6px);
  width: 17rem;
  background: var(--bg-card);
  border: 1px solid var(--line-strong);
  border-radius: 0.85rem;
  padding: 0.85rem;
  box-shadow: 0 18px 38px -10px rgba(26, 24, 23, 0.18);
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: opacity 0.18s ease, transform 0.18s ease;
  z-index: 40;
}

.letter-nav__item:hover .letter-popover,
.letter-nav__item:focus-within .letter-popover {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
  transform: translateX(-50%) translateY(0);
}

/* Каталожные карточки выставок */
.cards {
  display: grid;
  gap: 1.25rem;
  grid-template-columns: repeat(auto-fill, minmax(19rem, 1fr));
  padding: 0;
  list-style: none;
}

.cards li {
  position: relative;
  border: 1px solid var(--line);
  background: var(--bg-card);
  padding: 1.35rem;
  border-radius: 1rem;
  overflow: hidden;
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
}

.cards li:hover {
  transform: translateY(-3px);
  border-color: var(--accent);
  box-shadow: 0 14px 30px -12px rgba(26, 24, 23, 0.1);
}`,
  },
  {
    id: 'step-4',
    phase: 'Этап 4 · Статический JSON-индекс без плагинов Jekyll',
    title: 'Генерация site/search-index.json на чистом Liquid для GitHub Pages',
    filePath: 'site/search-index.json',
    language: 'json / liquid',
    summary:
      'Так как в site/_config.yml задано plugins: [], мы создаём файл site/search-index.json с пустым YAML Front Matter. При сборке Jekyll автоматически сгенерирует JSON со всеми 271 выставками для мгновенного поиска ⌘K и генератора «Случайная выставка дня».',
    highlights: [
      '100% совместимость с GitHub Pages при plugins: []',
      'Содержит заголовок, букву, URL, краткое описание и признак наличия фотографии в статье',
    ],
    code: `---
layout: null
permalink: /search-index.json
---
[
{%- assign sorted_exhibitions = site.exhibitions | sort: "order" -%}
{%- for item in sorted_exhibitions -%}
  {%- assign preview = item.content | strip_html | normalize_whitespace | strip | truncatewords: 24, "…" -%}
  {%- assign has_image = false -%}
  {%- if item.content contains "<img" or item.content contains "![" -%}
    {%- assign has_image = true -%}
  {%- endif -%}
  {
    "title": {{ item.title | jsonify }},
    "letter": {{ item.letter | jsonify }},
    "order": {{ item.order | default: 0 }},
    "featured": {{ item.featured | default: false }},
    "hasImage": {{ has_image }},
    "url": {{ item.url | relative_url | jsonify }},
    "preview": {{ preview | jsonify }}
  }{% unless forloop.last %},{% endunless %}
{%- endfor -%}
]`,
  },
  {
    id: 'step-5',
    phase: 'Этап 5 · Обновление карточек и страницы указателя',
    title: 'Каталожные карточки (site/_includes/cards.html) и Указатель (site/contents/index.html)',
    filePath: 'site/_includes/cards.html & site/contents/index.html',
    language: 'liquid / html',
    summary:
      'Обновляет разметку карточек выставок (добавляет каталожный номер item.order, бейдж буквы, индикатор фото-примера) и превращает страницу /contents/ в двухколоночный алфавитный гроссбух с плавающей навигацией.',
    highlights: [
      'Автоматическое определение наличия фото-примера в тексте выставки (item.content contains "<img")',
      'Якорные секции #letter-А .. #letter-Я на странице /contents/ для мгновенного скролла',
    ],
    code: `{%- comment -%} Файл: site/_includes/cards.html {%- endcomment -%}
<ul class="cards">
{%- for item in include.items -%}
  {%- assign preview = item.content | replace: "</p>", "</p> " | strip_html | normalize_whitespace | strip | truncatewords: 22, "…" -%}
  {%- assign has_photo = false -%}
  {%- if item.content contains "<img" -%}{%- assign has_photo = true -%}{%- endif -%}
  <li class="catalog-card">
    <div class="catalog-card__meta">
      <span class="catalog-card__letter">{{ item.letter }}</span>
      <span class="catalog-card__num">КАТ. № {{ item.order | prepend: "000" | slice: -3, 3 }}</span>
      {%- if has_photo -%}<span class="catalog-card__photo-badge">Фото</span>{%- endif -%}
    </div>
    <h3><a href="{{ item.url | relative_url }}">{{ item.title | escape }}</a></h3>
    {%- if preview != "" -%}<p>{{ preview | escape_once }}</p>{%- endif -%}
    <div class="catalog-card__footer">
      <span class="catalog-card__hole" aria-hidden="true"></span>
      <a class="catalog-card__more" href="{{ item.url | relative_url }}">Открыть карточку →</a>
    </div>
  </li>
{%- endfor -%}
</ul>`,
  },
];

const MASTER_AGENT_PROMPT = `Ты — Senior Design Engineer и специалист по статическим сайтам Jekyll.
Твоя задача — выполнить полный редизайн статического сайта в папке \`site/\` репозитория \`r2force/glossary\` («Книга – Выставка – Читатель»: глоссарий нетрадиционных форм книжных выставок, ЦГДБ г. Уфы).

### Ограничения и архитектура проекта:
1. Генератор: Jekyll (\`site/_config.yml\`, \`baseurl: "/glossary"\`, \`plugins: []\`). Не добавляй сторонние Ruby-гемы, всё должно собираться на стандартном GitHub Pages.
2. Сохрани все существующие коллекции и URL: \`_exhibitions\` (\`/exhibitions/:name/\`) и \`_sections\` (\`/sections/:name/\`).
3. Эстетика: «Современный библиофильский архив и кураторский каталог» (тёплая архивная бумага \`#FAF6F0\`, кремовые плашки \`#F3ECE2\`, глубокие чернила \`#1A1817\`, терракотовый книжный переплёт \`#9E3B24\`, охра \`#C88A32\`).
4. Шрифты (Google Fonts в \`_includes/head.html\`): \`Cormorant Garamond\` (заголовки и буквицы), \`Plus Jakarta Sans\` (основной текст и навигация), \`JetBrains Mono\` (каталожные номера и счётчики).

### Шаги выполнения:
1. В \`site/_includes/head.html\` подключи шрифты Google Fonts и скрипт \`/assets/site.js\` (defer).
2. Обнови \`site/_includes/letter-nav.html\`: выведи все 33 буквы русского алфавита (27 активных со ссылками на \`sec.url\`, динамическим счётчиком \`site.exhibitions | where: "letter", letter | size\` и полоской плотности + 6 неактивных букв Ё, Й, Щ, Ъ, Ы, Ь с деликатной штриховкой). Добавь всплывающий при наведении поповер \`.letter-popover\` с первыми 5 ссылками на выставки данной буквы.
3. Создай \`site/search-index.json\` с использованием Liquid для генерации индекса всех 271 выставок на этапе сборки.
4. Создай \`site/assets/site.js\`: реализуй магнитный Fisheye-эффект для букв алфавита при наведении курсора, эффект радиального прожектора (\`--mouse-x\`, \`--mouse-y\`) для карточек \`.cards li\`, быстрый поиск по \`search-index.json\` по клавише \`⌘K\` / \`/\`, генератор «Случайная форма выставки» и навигацию стрелками \`←\` / \`→\` на страницах выставок.
5. Обнови \`site/_includes/cards.html\`, \`site/_layouts/home.html\`, \`site/_layouts/exhibition.html\` и \`site/contents/index.html\` в стиле библиотечных каталожных карточек с перфорацией, буквицей и музейными рамками для иллюстраций из \`images/stories/exhibition/\`.
6. Полностью обнови \`site/assets/site.css\` с адаптивной сеткой, поддержкой \`prefers-reduced-motion\` и стилями печати.`;

export const AgentBlueprintView: React.FC<{
  onSwitchToPreview: () => void;
}> = ({ onSwitchToPreview }) => {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [activeStepId, setActiveStepId] = useState<string>(AGENT_STEPS[0].id);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2200);
  };

  const activeStep = AGENT_STEPS.find((s) => s.id === activeStepId) || AGENT_STEPS[0];

  return (
    <div className="space-y-8">
      {/* Hero Banner of the Agent Plan */}
      <div className="rounded-3xl border border-[#E2D9CC] bg-gradient-to-br from-[#FFFFFF] via-[#FAF6F0] to-[#F3ECE2] p-6 sm:p-8 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#9E3B24]/10 text-[#9E3B24] text-xs font-semibold mb-3">
              <FolderGit2 className="w-3.5 h-3.5" />
              <span>Техническое задание и архитектура для репозитория r2force/glossary/tree/main/site</span>
            </div>
            <h1 className="font-serif-editorial text-3xl sm:text-4xl lg:text-5xl font-bold text-[#1A1817] leading-tight">
              Подробный план редизайна для ИИ-агента + примеры кода
            </h1>
            <p className="text-sm sm:text-base text-[#4A443F] mt-3 leading-relaxed">
              Мы проанализировали текущую структуру Jekyll-сайта ЦГДБ г. Уфы (27 разделов в{' '}
              <code className="font-mono-archival text-xs bg-[#F3ECE2] px-1.5 py-0.5 rounded">_sections/</code>,
              271 карточка в{' '}
              <code className="font-mono-archival text-xs bg-[#F3ECE2] px-1.5 py-0.5 rounded">_exhibitions/</code>,
              список букв в{' '}
              <code className="font-mono-archival text-xs bg-[#F3ECE2] px-1.5 py-0.5 rounded">_data/alphabet.yml</code>{' '}
              и минималистичный 53-строчный{' '}
              <code className="font-mono-archival text-xs bg-[#F3ECE2] px-1.5 py-0.5 rounded">assets/site.css</code>).
              Ниже представлен готовый пошаговый план модернизации без нарушения совместимости с GitHub Pages (<code className="font-mono-archival text-xs">plugins: []</code>).
            </p>
          </div>

          <div className="flex flex-col sm:flex-row lg:flex-col gap-3 shrink-0">
            <button
              type="button"
              onClick={() => handleCopy(MASTER_AGENT_PROMPT, 'master-prompt')}
              className="inline-flex items-center justify-center gap-2 px-5 py-3.5 rounded-2xl bg-[#9E3B24] hover:bg-[#B8462B] text-white text-sm font-semibold shadow-sm transition-all cursor-pointer"
            >
              {copiedId === 'master-prompt' ? (
                <>
                  <Check className="w-4 h-4" />
                  <span>Master-промпт скопирован!</span>
                </>
              ) : (
                <>
                  <Terminal className="w-4 h-4" />
                  <span>Скопировать промпт для агента</span>
                </>
              )}
            </button>
            <button
              type="button"
              onClick={onSwitchToPreview}
              className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-white hover:bg-[#F3ECE2] text-[#1A1817] border border-[#E2D9CC] text-sm font-medium transition-all cursor-pointer"
            >
              <span>Смотреть живой пример</span>
              <ArrowRight className="w-4 h-4 text-[#9E3B24]" />
            </button>
          </div>
        </div>

        {/* Audit Summary Cards: Current Repo vs Proposed Redesign */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-7 pt-6 border-t border-[#E2D9CC]">
          <div className="rounded-2xl bg-white/80 border border-[#E2D9CC] p-4">
            <div className="flex items-center gap-2 text-xs font-mono-archival uppercase text-[#9E3B24] mb-1.5">
              <Compass className="w-4 h-4" />
              <span>1. Алфавитный указатель А–Я</span>
            </div>
            <p className="text-xs text-[#4A443F] leading-relaxed">
              <strong>Было:</strong> плоский список из 27 букв без счётчиков и превью.
              <br />
              <strong>Станет:</strong> интерактивная матрица всех 33 букв с количеством выставок, тепловой полоской, поповером быстрых ссылок при наведении и магнитным Fisheye-доком на TS.
            </p>
          </div>

          <div className="rounded-2xl bg-white/80 border border-[#E2D9CC] p-4">
            <div className="flex items-center gap-2 text-xs font-mono-archival uppercase text-[#2E5A44] mb-1.5">
              <BookOpen className="w-4 h-4" />
              <span>2. Эстетика каталожных карточек</span>
            </div>
            <p className="text-xs text-[#4A443F] leading-relaxed">
              <strong>Было:</strong> простые прямоугольники с рамкой 1px.
              <br />
              <strong>Станет:</strong> тактильные библиотечные формуляры с каталожным индексом (<code className="font-mono-archival">КАТ. № 019</code>), перфорацией, бейджем наличия фото и радиальным свечением за курсором.
            </p>
          </div>

          <div className="rounded-2xl bg-white/80 border border-[#E2D9CC] p-4">
            <div className="flex items-center gap-2 text-xs font-mono-archival uppercase text-[#C88A32] mb-1.5">
              <Cpu className="w-4 h-4" />
              <span>3. Дизайнерские фичи JS / TS</span>
            </div>
            <p className="text-xs text-[#4A443F] leading-relaxed">
              <strong>Было:</strong> 0 строк JS, отсутствие поиска по 271 термину.
              <br />
              <strong>Станет:</strong> мгновенный поиск <code className="font-mono-archival">⌘K</code> через автогенерируемый Liquid JSON, рулетка «Случайная форма выставки», хоткеи русских букв с клавиатуры и ScrollSpy.
            </p>
          </div>
        </div>
      </div>

      {/* Interactive Code Explorer by File / Step */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Sidebar: 5 Implementation Phases */}
        <div className="lg:col-span-5 space-y-3">
          <h2 className="font-serif-editorial text-2xl font-bold text-[#1A1817] px-1">
            Пошаговый план файлов в <code className="font-mono-archival text-base text-[#9E3B24]">site/</code>
          </h2>
          {AGENT_STEPS.map((step) => {
            const isActive = step.id === activeStep.id;
            return (
              <button
                key={step.id}
                type="button"
                onClick={() => setActiveStepId(step.id)}
                className={`w-full text-left rounded-2xl p-4 border transition-all cursor-pointer ${
                  isActive
                    ? 'bg-[#FFFFFF] border-[#9E3B24] shadow-md ring-1 ring-[#9E3B24]/20'
                    : 'bg-[#FFFFFF]/70 border-[#E2D9CC] hover:bg-[#FFFFFF] hover:border-[#C5B9A8]'
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="font-mono-archival text-[11px] font-semibold text-[#9E3B24]">
                    {step.phase}
                  </span>
                  <span className="font-mono-archival text-[11px] px-2 py-0.5 rounded bg-[#F3ECE2] text-[#4A443F]">
                    {step.filePath}
                  </span>
                </div>
                <h3 className="font-serif-editorial text-lg font-bold text-[#1A1817] leading-snug">
                  {step.title}
                </h3>
                <p className="text-xs text-[#7A7167] mt-1.5 line-clamp-2">
                  {step.summary}
                </p>
              </button>
            );
          })}

          {/* Ready Master Prompt Box */}
          <div className="rounded-2xl border border-[#E2D9CC] bg-[#F3ECE2]/70 p-4 mt-4">
            <div className="flex items-center justify-between gap-2 mb-2">
              <span className="inline-flex items-center gap-1.5 text-xs font-bold text-[#1A1817]">
                <Sparkles className="w-4 h-4 text-[#9E3B24]" />
                Готовый системный промпт для агента
              </span>
              <button
                type="button"
                onClick={() => handleCopy(MASTER_AGENT_PROMPT, 'sidebar-prompt')}
                className="text-xs font-semibold text-[#9E3B24] hover:underline flex items-center gap-1 cursor-pointer"
              >
                {copiedId === 'sidebar-prompt' ? (
                  <>
                    <Check className="w-3.5 h-3.5" /> Скопировано
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" /> Копировать
                  </>
                )}
              </button>
            </div>
            <pre className="text-[11px] font-mono-archival text-[#4A443F] bg-white/90 p-3 rounded-xl border border-[#E2D9CC] max-h-48 overflow-y-auto whitespace-pre-wrap">
              {MASTER_AGENT_PROMPT}
            </pre>
          </div>
        </div>

        {/* Right Panel: Selected File Specification & Code */}
        <div className="lg:col-span-7 rounded-3xl border border-[#E2D9CC] bg-[#FFFFFF] overflow-hidden shadow-sm">
          <div className="p-6 border-b border-[#E2D9CC] bg-[#FAF6F0]/60">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
              <span className="inline-flex items-center gap-1.5 font-mono-archival text-xs font-semibold text-[#9E3B24] bg-[#9E3B24]/10 px-2.5 py-1 rounded-lg">
                <FileCode className="w-3.5 h-3.5" />
                {activeStep.filePath}
              </span>
              <span className="font-mono-archival text-xs text-[#7A7167]">
                Язык: {activeStep.language}
              </span>
            </div>

            <h3 className="font-serif-editorial text-2xl font-bold text-[#1A1817]">
              {activeStep.title}
            </h3>
            <p className="text-sm text-[#4A443F] mt-2 leading-relaxed">
              {activeStep.summary}
            </p>

            <div className="mt-4 space-y-1.5">
              {activeStep.highlights.map((hl, idx) => (
                <div key={idx} className="flex items-start gap-2 text-xs text-[#1A1817]">
                  <CheckCircle2 className="w-4 h-4 text-[#2E5A44] shrink-0 mt-0.5" />
                  <span>{hl}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Code Block with Copy Button */}
          <div className="bg-[#1A1817] text-[#FAF6F0] p-4 sm:p-6">
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-white/10">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#9E3B24]" />
                <span className="w-2.5 h-2.5 rounded-full bg-[#C88A32]" />
                <span className="w-2.5 h-2.5 rounded-full bg-[#2E5A44]" />
                <span className="font-mono-archival text-xs text-white/70 ml-2">
                  {activeStep.filePath}
                </span>
              </div>
              <button
                type="button"
                onClick={() => handleCopy(activeStep.code, activeStep.id)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-xs font-mono-archival text-white transition-colors cursor-pointer"
              >
                {copiedId === activeStep.id ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-[#4ADE80]" />
                    <span>Скопировано</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Копировать код</span>
                  </>
                )}
              </button>
            </div>
            <pre className="font-mono-archival text-xs sm:text-[13px] leading-relaxed overflow-x-auto text-[#F3ECE2]">
              <code>{activeStep.code}</code>
            </pre>
          </div>
        </div>
      </div>

      {/* Designer JS/TS Showcase Checklist */}
      <div className="rounded-2xl border border-[#E2D9CC] bg-white p-6">
        <div className="flex items-center gap-2 mb-4">
          <Layers className="w-5 h-5 text-[#9E3B24]" />
          <h3 className="font-serif-editorial text-2xl font-bold text-[#1A1817]">
            Шпаргалка по дизайнерским JS/TS-фичам, заложенным в проект
          </h3>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-[#FAF6F0] border border-[#E2D9CC]">
            <div className="font-mono-archival text-xs text-[#9E3B24] font-semibold mb-1">
              01 · MAGNETIC DOCK
            </div>
            <div className="font-semibold text-sm text-[#1A1817] mb-1">
              Косинусная волна букв А–Я
            </div>
            <p className="text-xs text-[#4A443F]">
              При ведении курсора по алфавиту соседние литеры плавно увеличиваются по формуле <code className="font-mono-archival">(1 + cos(π·d/R))/2</code>, создавая тактильный отклик.
            </p>
          </div>
          <div className="p-4 rounded-xl bg-[#FAF6F0] border border-[#E2D9CC]">
            <div className="font-mono-archival text-xs text-[#9E3B24] font-semibold mb-1">
              02 · HOVER LINK POPOVER
            </div>
            <div className="font-semibold text-sm text-[#1A1817] mb-1">
              Мгновенные ссылки без клика
            </div>
            <p className="text-xs text-[#4A443F]">
              Каждая буква показывает количество терминов, полоску наполненности раздела и прямые ссылки на выставки этого раздела.
            </p>
          </div>
          <div className="p-4 rounded-xl bg-[#FAF6F0] border border-[#E2D9CC]">
            <div className="font-mono-archival text-xs text-[#9E3B24] font-semibold mb-1">
              03 · CURSOR SPOTLIGHT
            </div>
            <div className="font-semibold text-sm text-[#1A1817] mb-1">
              Радиальная подсветка карточек
            </div>
            <p className="text-xs text-[#4A443F]">
              Тёплое терракотовое свечение следует за курсором внутри каждой каталожной карточки через CSS-переменные <code className="font-mono-archival">--mouse-x/y</code>.
            </p>
          </div>
          <div className="p-4 rounded-xl bg-[#FAF6F0] border border-[#E2D9CC]">
            <div className="font-mono-archival text-xs text-[#9E3B24] font-semibold mb-1">
              04 · COMMAND PALETTE ⌘K
            </div>
            <div className="font-semibold text-sm text-[#1A1817] mb-1">
              Поиск + Рулетка для библиотекаря
            </div>
            <p className="text-xs text-[#4A443F]">
              Мгновенная фильтрация всех 271 форм выставок по названию, категории или аксессуарам + кнопка «Случайная идея выставки».
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
