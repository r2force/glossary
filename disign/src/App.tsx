import { useState, useEffect } from 'react';
import {
  ALL_CYRILLIC_LETTERS,
  EXHIBITIONS_DATA,
  ACCESSORY_TYPES,
  CLASSIFICATION_TAXONOMY,
  ExhibitionItem,
} from './data/glossaryData';
import { AlphabetNavigator } from './components/AlphabetNavigator';
import { CatalogCard } from './components/CatalogCard';
import { AgentBlueprintView } from './components/AgentBlueprintView';
import { CommandPaletteModal } from './components/CommandPaletteModal';
import {
  BookOpen,
  Search,
  Shuffle,
  Sparkles,
  FileCode2,
  Eye,
  ArrowLeft,
  ArrowRight,
  Camera,
  Mail,
  MapPin,
  Check,
  Copy,
  ChevronRight,
  Library,
  Columns,
  ExternalLink,
  Filter,
} from 'lucide-react';

type WorkspaceTab = 'live-preview' | 'agent-plan';
type SitePage = 'home' | 'contents' | 'section' | 'exhibition' | 'conclusion';

export function App() {
  const [workspaceTab, setWorkspaceTab] = useState<WorkspaceTab>('live-preview');
  const [sitePage, setSitePage] = useState<SitePage>('home');
  const [selectedLetter, setSelectedLetter] = useState<string>('А');
  const [selectedExhibition, setSelectedExhibition] = useState<ExhibitionItem>(
    EXHIBITIONS_DATA[3] // Выставка – ай-стоппер
  );
  const [selectedCategory, setSelectedCategory] = useState<string>('Все');
  const [isCmdkOpen, setIsCmdkOpen] = useState<boolean>(false);
  const [compareLegacyCss, setCompareLegacyCss] = useState<boolean>(false);
  const [copiedCitation, setCopiedCitation] = useState<boolean>(false);

  // Global keyboard shortcuts (⌘K for search, ← / → for exhibition pager)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCmdkOpen((prev) => !prev);
      }
      if (
        workspaceTab === 'live-preview' &&
        sitePage === 'exhibition' &&
        !isCmdkOpen
      ) {
        const idx = EXHIBITIONS_DATA.findIndex(
          (item) => item.slug === selectedExhibition.slug
        );
        if (e.key === 'ArrowLeft' && idx > 0) {
          setSelectedExhibition(EXHIBITIONS_DATA[idx - 1]);
        } else if (e.key === 'ArrowRight' && idx < EXHIBITIONS_DATA.length - 1) {
          setSelectedExhibition(EXHIBITIONS_DATA[idx + 1]);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [workspaceTab, sitePage, selectedExhibition, isCmdkOpen]);

  const handleOpenLetterSection = (letter: string) => {
    setSelectedLetter(letter);
    setSitePage('section');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleOpenExhibition = (item: ExhibitionItem) => {
    setSelectedExhibition(item);
    setSelectedLetter(item.letter);
    setSitePage('exhibition');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleOpenExhibitionBySlug = (slug: string, letter: string) => {
    const existing = EXHIBITIONS_DATA.find((e) => e.slug === slug);
    if (existing) {
      handleOpenExhibition(existing);
      return;
    }
    // Synthesize a realistic card if user clicks one of the 271 sample links not in top 19 detailed items
    const letterObj = ALL_CYRILLIC_LETTERS.find((l) => l.letter === letter);
    const sample = letterObj?.sampleTerms.find((t) => t.slug === slug);
    const synthesized: ExhibitionItem = {
      id: String(Math.floor(Math.random() * 200) + 50),
      slug,
      url: `/glossary/exhibitions/${slug}/`,
      title: sample?.title || 'Форма книжной выставки',
      letter,
      sectionSlug: letterObj?.slug || 'a',
      order: letterObj?.order || 1,
      isNewEdition: sample?.isNew,
      category: 'Интерактивная',
      audience: 'Читатели детской библиотеки',
      definition: `${
        sample?.title || 'Данная нетрадиционная форма выставки'
      } — специализированная форма экспозиционной работы из раздела «${letter}» глоссария «Книга – Выставка – Читатель» (ЦГДБ г. Уфы), направленная на образное раскрытие книжного фонда и вовлечение юных читателей в диалог с книгой.`,
      example: `Практическая разработка библиотек Централизованной системы детских библиотек ГО г. Уфа (раздел «${letter}», URL: /glossary/exhibitions/${slug}/).`,
      accessories: ['Знаковые символы', 'Иллюстративный ряд', 'Читательские закладки'],
    };
    handleOpenExhibition(synthesized);
  };

  const handleRandomIdea = () => {
    const randomItem =
      EXHIBITIONS_DATA[Math.floor(Math.random() * EXHIBITIONS_DATA.length)];
    setWorkspaceTab('live-preview');
    handleOpenExhibition(randomItem);
  };

  const categories = [
    'Все',
    'Интерактивная',
    'Ай-стоппер',
    'Игровая',
    'Предметная',
    'Визуально-образная',
  ];

  const filteredExhibitions =
    selectedCategory === 'Все'
      ? EXHIBITIONS_DATA
      : EXHIBITIONS_DATA.filter((item) => item.category === selectedCategory);

  const currentLetterObj =
    ALL_CYRILLIC_LETTERS.find((l) => l.letter === selectedLetter) ||
    ALL_CYRILLIC_LETTERS[0];

  const currentExIndex = EXHIBITIONS_DATA.findIndex(
    (e) => e.slug === selectedExhibition.slug
  );
  const prevExhibition =
    currentExIndex > 0 ? EXHIBITIONS_DATA[currentExIndex - 1] : null;
  const nextExhibition =
    currentExIndex >= 0 && currentExIndex < EXHIBITIONS_DATA.length - 1
      ? EXHIBITIONS_DATA[currentExIndex + 1]
      : null;

  return (
    <div className="min-h-screen paper-grain flex flex-col">
      {/* TOP DESIGNER STUDIO BAR (Switches between Live Prototype & Agent Plan) */}
      <div className="sticky top-0 z-40 bg-[#1A1817] text-[#FAF6F0] border-b border-white/10 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-2.5 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#9E3B24] text-white font-mono-archival text-xs font-semibold">
              <Sparkles className="w-3.5 h-3.5" />
              РЕДИЗАЙН + ПЛАН
            </span>
            <span className="text-xs sm:text-sm text-white/85 font-medium hidden md:inline">
              Репозиторий:{' '}
              <a
                href="https://github.com/r2force/glossary/tree/main/site"
                target="_blank"
                rel="noreferrer"
                className="text-[#F3ECE2] underline decoration-[#C88A32] hover:text-white inline-flex items-center gap-1"
              >
                r2force/glossary/tree/main/site
                <ExternalLink className="w-3 h-3" />
              </a>
            </span>
          </div>

          {/* Primary Switcher: Live Example vs Agent Plan */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-xl bg-white/10 p-1">
              <button
                type="button"
                onClick={() => setWorkspaceTab('live-preview')}
                className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
                  workspaceTab === 'live-preview'
                    ? 'bg-[#FAF6F0] text-[#1A1817] shadow-xs'
                    : 'text-white/80 hover:text-white'
                }`}
              >
                <Eye className="w-4 h-4 text-[#9E3B24]" />
                <span>Живой пример сайта</span>
              </button>
              <button
                type="button"
                onClick={() => setWorkspaceTab('agent-plan')}
                className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
                  workspaceTab === 'agent-plan'
                    ? 'bg-[#FAF6F0] text-[#1A1817] shadow-xs'
                    : 'text-white/80 hover:text-white'
                }`}
              >
                <FileCode2 className="w-4 h-4 text-[#C88A32]" />
                <span>План для агента + Код (5 этапов)</span>
              </button>
            </div>

            {workspaceTab === 'live-preview' && (
              <button
                type="button"
                onClick={() => setCompareLegacyCss((v) => !v)}
                title="Сравнить исходный 53-строчный site.css и новый дизайн"
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-mono-archival border transition-all cursor-pointer ${
                  compareLegacyCss
                    ? 'bg-[#C88A32] text-[#1A1817] border-[#C88A32] font-bold'
                    : 'bg-white/5 text-white/85 border-white/15 hover:bg-white/10'
                }`}
              >
                <Columns className="w-3.5 h-3.5" />
                <span>{compareLegacyCss ? 'Режим: Старый CSS' : 'До / После'}</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* WORKSPACE CONTENT */}
      {workspaceTab === 'agent-plan' ? (
        <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8 sm:py-10 flex-1 w-full">
          <AgentBlueprintView
            onSwitchToPreview={() => setWorkspaceTab('live-preview')}
          />
        </main>
      ) : compareLegacyCss ? (
        /* LEGACY CSS COMPARISON VIEW (Shows exact original 53-line site.css look alongside switch back) */
        <div className="bg-[#fbf8f5] text-[#1d1b1a] min-h-screen font-serif flex-1">
          <div className="max-w-[56rem] mx-auto px-5 py-4">
            <div className="mb-6 p-4 rounded-xl bg-[#9E3B24] text-white font-sans flex flex-wrap items-center justify-between gap-3">
              <div className="text-xs sm:text-sm">
                <strong>Режим демонстрации «КАК БЫЛО»:</strong> оригинальная вёрстка из{' '}
                <code>r2force/glossary/main/site/assets/site.css</code> (53 строки CSS, без счётчиков букв, без поиска и превью).
              </div>
              <button
                type="button"
                onClick={() => setCompareLegacyCss(false)}
                className="px-3.5 py-1.5 rounded-lg bg-white text-[#9E3B24] text-xs font-bold cursor-pointer"
              >
                Вернуться в Новый дизайн →
              </button>
            </div>

            <header className="border-b border-[#ded6cf] bg-white p-4 mb-6 flex flex-wrap justify-between items-baseline">
              <div>
                <div className="font-bold text-lg">«Книга – Выставка – Читатель»</div>
                <div className="text-xs text-[#6b625c]">
                  глоссарий нетрадиционных форм книжных выставок
                </div>
              </div>
              <nav className="flex gap-4 text-sm text-[#7d3d2e]">
                <a href="#home" onClick={(e) => { e.preventDefault(); setCompareLegacyCss(false); }}>Главная</a>
                <a href="#contents" onClick={(e) => { e.preventDefault(); setCompareLegacyCss(false); }}>Указатель</a>
                <a href="#conclusion" onClick={(e) => { e.preventDefault(); setCompareLegacyCss(false); }}>Заключение</a>
              </nav>
            </header>

            <h1 className="text-3xl font-bold mb-2">«Книга – Выставка – Читатель»</h1>
            <p className="text-[#6b625c] mb-4">глоссарий нетрадиционных форм книжных выставок</p>
            <h2 className="text-xl font-bold mb-2">Алфавитный указатель (оригинальный вид)</h2>
            <ul className="flex flex-wrap gap-1.5 list-none p-0 mb-6">
              {ALL_CYRILLIC_LETTERS.filter((l) => l.active).map((l) => (
                <li key={l.letter}>
                  <a
                    href={`#${l.slug}`}
                    onClick={(e) => {
                      e.preventDefault();
                      setCompareLegacyCss(false);
                      handleOpenLetterSection(l.letter);
                    }}
                    className="inline-block min-w-[2rem] text-center px-2 py-1 border border-[#ded6cf] rounded bg-white text-[#7d3d2e] no-underline"
                  >
                    {l.letter}
                  </a>
                </li>
              ))}
            </ul>

            <h2 className="text-xl font-bold mb-2">Избранные выставки (оригинальные карточки)</h2>
            <ul className="grid grid-cols-1 sm:grid-cols-2 gap-4 list-none p-0">
              {EXHIBITIONS_DATA.slice(0, 4).map((item) => (
                <li key={item.id} className="border border-[#ded6cf] bg-white p-4 rounded">
                  <h3 className="font-bold text-base mb-1 text-[#7d3d2e] underline">
                    {item.title}
                  </h3>
                  <p className="text-sm text-[#6b625c] m-0">{item.definition}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : (
        /* REDESIGNED SITE SHOWCASE (Modern Archival & Tactile Library Editorial) */
        <div className="flex-1 flex flex-col">
          {/* REDESIGNED SITE HEADER (_includes/header.html + _includes/nav.html) */}
          <header className="border-b border-[#E2D9CC] bg-[#FFFFFF]/85 backdrop-blur-md">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              {/* Brand Identity */}
              <div className="flex items-center gap-3.5">
                <button
                  type="button"
                  onClick={() => setSitePage('home')}
                  className="w-12 h-12 rounded-2xl bg-[#9E3B24] text-white flex flex-col items-center justify-center shadow-sm hover:bg-[#B8462B] transition-colors shrink-0 cursor-pointer"
                  title="На главную страницу"
                >
                  <BookOpen className="w-5 h-5" />
                  <span className="font-mono-archival text-[9px] tracking-widest mt-0.5">
                    УФА
                  </span>
                </button>
                <div>
                  <button
                    type="button"
                    onClick={() => setSitePage('home')}
                    className="text-left group cursor-pointer"
                  >
                    <span className="font-serif-editorial text-2xl sm:text-3xl font-bold text-[#1A1817] group-hover:text-[#9E3B24] transition-colors tracking-tight block leading-none">
                      «Книга – Выставка – Читатель»
                    </span>
                    <span className="text-xs sm:text-sm text-[#7A7167] block mt-1">
                      глоссарий нетрадиционных форм книжных выставок · ЦГДБ г. Уфы
                    </span>
                  </button>
                </div>
              </div>

              {/* Site Navigation (_data/navigation.yml) + Designer Interactive Tools */}
              <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                <nav
                  aria-label="Основная навигация сайта"
                  className="inline-flex items-center rounded-xl bg-[#F3ECE2] p-1 border border-[#E2D9CC]"
                >
                  <button
                    type="button"
                    onClick={() => setSitePage('home')}
                    aria-current={sitePage === 'home' ? 'page' : undefined}
                    className={`px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all cursor-pointer ${
                      sitePage === 'home'
                        ? 'bg-white text-[#9E3B24] font-semibold shadow-xs'
                        : 'text-[#4A443F] hover:text-[#1A1817]'
                    }`}
                  >
                    Главная
                  </button>
                  <button
                    type="button"
                    onClick={() => setSitePage('contents')}
                    aria-current={sitePage === 'contents' ? 'page' : undefined}
                    className={`px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all cursor-pointer ${
                      sitePage === 'contents'
                        ? 'bg-white text-[#9E3B24] font-semibold shadow-xs'
                        : 'text-[#4A443F] hover:text-[#1A1817]'
                    }`}
                  >
                    Алфавитный указатель (А–Я)
                  </button>
                  <button
                    type="button"
                    onClick={() => setSitePage('conclusion')}
                    aria-current={sitePage === 'conclusion' ? 'page' : undefined}
                    className={`px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all cursor-pointer ${
                      sitePage === 'conclusion'
                        ? 'bg-white text-[#9E3B24] font-semibold shadow-xs'
                        : 'text-[#4A443F] hover:text-[#1A1817]'
                    }`}
                  >
                    Заключение
                  </button>
                </nav>

                {/* Instant Command Palette Trigger (⌘K) */}
                <button
                  type="button"
                  onClick={() => setIsCmdkOpen(true)}
                  className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#FAF6F0] hover:bg-white border border-[#E2D9CC] hover:border-[#9E3B24]/50 text-xs sm:text-sm text-[#4A443F] transition-all cursor-pointer shadow-2xs"
                >
                  <Search className="w-4 h-4 text-[#9E3B24]" />
                  <span>Поиск по 271 форме…</span>
                  <kbd className="font-mono-archival text-[10px] px-1.5 py-0.5 rounded bg-[#F3ECE2] text-[#7A7167] border border-[#E2D9CC]">
                    ⌘K
                  </kbd>
                </button>

                {/* Random Exhibition Idea Generator */}
                <button
                  type="button"
                  onClick={handleRandomIdea}
                  title="Случайная форма книжной выставки для вдохновения библиотекаря"
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#9E3B24]/10 hover:bg-[#9E3B24] text-[#9E3B24] hover:text-white text-xs sm:text-sm font-semibold transition-all cursor-pointer"
                >
                  <Shuffle className="w-4 h-4" />
                  <span className="hidden sm:inline">Случайная выставка</span>
                </button>
              </div>
            </div>
          </header>

          {/* MAIN PAGE VIEWPORT */}
          <main id="content" className="max-w-7xl mx-auto px-4 sm:px-6 py-8 sm:py-10 flex-1 w-full">
            {/* =========================================================
                PAGE 1: HOME (_layouts/home.html + site/index.html)
               ========================================================= */}
            {sitePage === 'home' && (
              <div className="space-y-12">
                {/* Editorial Hero Section */}
                <section className="relative rounded-3xl border border-[#E2D9CC] bg-gradient-to-br from-[#FFFFFF] via-[#FAF6F0] to-[#F3ECE2] p-6 sm:p-10 overflow-hidden shadow-[0_16px_40px_-20px_rgba(26,24,23,0.08)]">
                  {/* Decorative oversized background Cyrillic watermark */}
                  <div
                    aria-hidden="true"
                    className="pointer-events-none select-none absolute -right-6 -bottom-12 font-serif-editorial text-[14rem] sm:text-[18rem] font-bold leading-none text-[#9E3B24]/[0.05]"
                  >
                    А–Я
                  </div>

                  <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
                    <div className="lg:col-span-8 space-y-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#9E3B24] text-white text-xs font-mono-archival uppercase tracking-wider">
                          <Library className="w-3.5 h-3.5" />
                          Справочное издание · 2-е переработанное
                        </span>
                        <span className="font-mono-archival text-xs px-3 py-1 rounded-full bg-white/90 border border-[#E2D9CC] text-[#4A443F]">
                          ЦГДБ г. Уфы
                        </span>
                      </div>

                      <h1 className="font-serif-editorial text-4xl sm:text-5xl lg:text-6xl font-bold text-[#1A1817] leading-[1.08] tracking-tight">
                        «Книга – Выставка – Читатель»
                      </h1>

                      <p className="font-serif-editorial italic text-xl sm:text-2xl text-[#9E3B24]">
                        «Организация книжных выставок — это наука, искусство, творчество.»
                      </p>

                      <p className="text-sm sm:text-base text-[#4A443F] max-w-2xl leading-relaxed">
                        Словарь узкоспециализированных терминов, систематизирующий более{' '}
                        <strong className="text-[#1A1817]">270 нетрадиционных форм выставочной работы</strong>{' '}
                        (включая <strong className="text-[#2E5A44]">72 новые интерактивные формы</strong>),
                        способствующих активному продвижению книги к юному читателю.
                      </p>

                      <div className="flex flex-wrap items-center gap-3 pt-2">
                        <button
                          type="button"
                          onClick={() => setSitePage('contents')}
                          className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-[#9E3B24] hover:bg-[#B8462B] text-white text-sm font-semibold shadow-sm transition-all cursor-pointer"
                        >
                          <span>Открыть полный указатель А–Я</span>
                          <ArrowRight className="w-4 h-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => setWorkspaceTab('agent-plan')}
                          className="inline-flex items-center gap-2 px-4 py-3 rounded-xl bg-white hover:bg-[#F3ECE2] text-[#1A1817] border border-[#E2D9CC] text-sm font-medium transition-all cursor-pointer"
                        >
                          <FileCode2 className="w-4 h-4 text-[#9E3B24]" />
                          <span>План редизайна и код для агента</span>
                        </button>
                      </div>
                    </div>

                    {/* Right Column: Archival Passport Card */}
                    <div className="lg:col-span-4">
                      <div className="rounded-2xl bg-white/95 border border-[#E2D9CC] p-5 shadow-xs space-y-4">
                        <div className="flex items-center justify-between border-b border-dashed border-[#E2D9CC] pb-3">
                          <span className="font-mono-archival text-xs uppercase text-[#7A7167]">
                            ФОРМУЛЯР ИЗДАНИЯ
                          </span>
                          <span className="font-mono-archival text-xs font-semibold text-[#9E3B24]">
                            ББК 78.37
                          </span>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                          <div className="p-3 rounded-xl bg-[#FAF6F0] border border-[#E2D9CC]">
                            <div className="font-serif-editorial text-3xl font-bold text-[#9E3B24]">
                              271
                            </div>
                            <div className="text-xs text-[#4A443F] mt-0.5">
                              форма книжных выставок в базе
                            </div>
                          </div>
                          <div className="p-3 rounded-xl bg-[#FAF6F0] border border-[#E2D9CC]">
                            <div className="font-serif-editorial text-3xl font-bold text-[#2E5A44]">
                              +72
                            </div>
                            <div className="text-xs text-[#4A443F] mt-0.5">
                              новые формы за последние 5 лет
                            </div>
                          </div>
                          <div className="p-3 rounded-xl bg-[#FAF6F0] border border-[#E2D9CC]">
                            <div className="font-serif-editorial text-3xl font-bold text-[#1A1817]">
                              27 / 33
                            </div>
                            <div className="text-xs text-[#4A443F] mt-0.5">
                              активных разделов алфавита А–Я
                            </div>
                          </div>
                          <div className="p-3 rounded-xl bg-[#FAF6F0] border border-[#E2D9CC]">
                            <div className="font-serif-editorial text-3xl font-bold text-[#C88A32]">
                              3 вида
                            </div>
                            <div className="text-xs text-[#4A443F] mt-0.5">
                              наглядности: образ, предмет, арт
                            </div>
                          </div>
                        </div>

                        <div className="text-[11px] text-[#7A7167] font-mono-archival pt-1 flex items-center justify-between">
                          <span>Адресат: Библиотекари, педагоги</span>
                          <span>г. Уфа</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </section>

                {/* CENTERPIECE: INTERACTIVE ALPHABET NAVIGATOR WITH LINKS */}
                <AlphabetNavigator
                  activeLetter={null}
                  onSelectLetter={handleOpenLetterSection}
                  onSelectExhibitionSlug={handleOpenExhibitionBySlug}
                  onOpenFullIndex={() => setSitePage('contents')}
                />

                {/* FEATURED EXHIBITIONS (Избранные выставки + Фильтр по форматам) */}
                <section className="space-y-5">
                  <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                    <div>
                      <div className="font-mono-archival text-xs uppercase tracking-wider text-[#9E3B24] mb-1">
                        КУРАТОРСКАЯ ПОДБОРКА · КАТАЛОЖНЫЕ КАРТОЧКИ
                      </div>
                      <h2 className="font-serif-editorial text-3xl sm:text-4xl font-bold text-[#1A1817]">
                        Избранные и нетрадиционные формы выставок
                      </h2>
                    </div>

                    {/* Category Filter Pills */}
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Filter className="w-4 h-4 text-[#7A7167] mr-1 hidden sm:inline" />
                      {categories.map((cat) => (
                        <button
                          key={cat}
                          type="button"
                          onClick={() => setSelectedCategory(cat)}
                          className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all cursor-pointer ${
                            selectedCategory === cat
                              ? 'bg-[#9E3B24] text-white shadow-xs'
                              : 'bg-white border border-[#E2D9CC] text-[#4A443F] hover:border-[#9E3B24]/50'
                          }`}
                        >
                          {cat}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {filteredExhibitions.map((item) => (
                      <CatalogCard
                        key={item.id}
                        item={item}
                        onSelect={handleOpenExhibition}
                        onSelectLetter={handleOpenLetterSection}
                      />
                    ))}
                  </div>
                </section>

                {/* REDESIGNED METHODOLOGICAL ESSAY FROM site/index.html */}
                <section className="rounded-3xl border border-[#E2D9CC] bg-white p-6 sm:p-10 space-y-8">
                  <div className="max-w-3xl">
                    <span className="font-mono-archival text-xs uppercase tracking-wider text-[#9E3B24]">
                      МЕТОДИЧЕСКОЕ ВВЕДЕНИЕ · О ГЛОССАРИИ
                    </span>
                    <h2 className="font-serif-editorial text-3xl sm:text-4xl font-bold text-[#1A1817] mt-1">
                      Три вида наглядности и архитектура аксессуаров выставки
                    </h2>
                    <p className="text-sm sm:text-base text-[#4A443F] mt-3 leading-relaxed editorial-dropcap">
                      На протяжении многих лет тема выставок не сходит со страниц профессиональной печати. Потенциал выставочной работы особенно эффективно используется в детской библиотеке, поскольку восприятие ребенка носит наглядно-образный характер. Оформление выставки включает три вида наглядности: образную, предметную и изобразительную.
                    </p>
                  </div>

                  {/* 4 Accessory Bento Cards */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {ACCESSORY_TYPES.map((acc) => (
                      <div
                        key={acc.title}
                        className="rounded-2xl border border-[#E2D9CC] bg-[#FAF6F0] p-5 flex flex-col justify-between"
                      >
                        <div>
                          <span
                            className="inline-block text-[11px] font-mono-archival font-semibold px-2.5 py-0.5 rounded-md text-white mb-2.5"
                            style={{ backgroundColor: acc.color }}
                          >
                            {acc.badge}
                          </span>
                          <h3 className="font-serif-editorial text-xl font-bold text-[#1A1817] mb-1.5">
                            {acc.title}
                          </h3>
                          <p className="text-xs text-[#4A443F] leading-relaxed mb-3">
                            {acc.description}
                          </p>
                        </div>
                        <div className="pt-3 border-t border-[#E2D9CC] text-xs font-medium text-[#1A1817]">
                          <span className="text-[#7A7167]">Состав: </span>
                          {acc.items}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Interactive Classification Matrix (11 признаков классификации из index.html) */}
                  <div className="pt-4 border-t border-[#E2D9CC]">
                    <h3 className="font-serif-editorial text-2xl font-bold text-[#1A1817] mb-4">
                      Паспорт классификации книжных выставок
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {CLASSIFICATION_TAXONOMY.map((row) => (
                        <div
                          key={row.criterion}
                          className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3.5 rounded-xl bg-[#FAF6F0]/70 border border-[#E2D9CC]"
                        >
                          <span className="font-semibold text-xs sm:text-sm text-[#9E3B24] shrink-0">
                            {row.criterion}
                          </span>
                          <span className="text-xs text-[#4A443F] sm:text-right">
                            {row.values}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </section>
              </div>
            )}

            {/* =========================================================
                PAGE 2: FULL ALPHABETICAL INDEX (site/contents/index.html)
               ========================================================= */}
            {sitePage === 'contents' && (
              <div className="space-y-8">
                {/* Breadcrumbs */}
                <nav className="flex items-center gap-2 text-xs text-[#7A7167]">
                  <button
                    type="button"
                    onClick={() => setSitePage('home')}
                    className="hover:text-[#9E3B24] cursor-pointer"
                  >
                    Главная
                  </button>
                  <ChevronRight className="w-3.5 h-3.5" />
                  <span className="text-[#1A1817] font-medium">
                    Алфавитный указатель (/contents/)
                  </span>
                </nav>

                <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                  <div>
                    <h1 className="font-serif-editorial text-4xl sm:text-5xl font-bold text-[#1A1817]">
                      Алфавитный указатель от А до Я
                    </h1>
                    <p className="text-sm sm:text-base text-[#4A443F] mt-1">
                      Всего выставок: <strong>271</strong> · Активных разделов:{' '}
                      <strong>27</strong>. Кликните на любую букву для быстрого перехода или выберите термин.
                    </p>
                  </div>
                </div>

                {/* Sticky Alphabet Navigator in Compact / Matrix mode */}
                <AlphabetNavigator
                  activeLetter={selectedLetter}
                  onSelectLetter={(letter) => {
                    setSelectedLetter(letter);
                    const el = document.getElementById(`index-letter-${letter}`);
                    el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                  }}
                  onSelectExhibitionSlug={handleOpenExhibitionBySlug}
                  defaultMode="compact"
                  compactHeader
                />

                {/* Complete 27-Section Directory with Links */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {ALL_CYRILLIC_LETTERS.filter((l) => l.active).map((sec) => (
                    <section
                      key={sec.letter}
                      id={`index-letter-${sec.letter}`}
                      className="rounded-2xl border border-[#E2D9CC] bg-white p-6 shadow-2xs hover:border-[#C5B9A8] transition-all"
                    >
                      <div className="flex items-center justify-between pb-3 mb-4 border-b border-[#E2D9CC]">
                        <div className="flex items-center gap-3">
                          <button
                            type="button"
                            onClick={() => handleOpenLetterSection(sec.letter)}
                            className="w-11 h-11 rounded-xl bg-[#FAF6F0] hover:bg-[#9E3B24] text-[#9E3B24] hover:text-white border border-[#E2D9CC] font-serif-editorial text-2xl font-bold flex items-center justify-center transition-colors cursor-pointer"
                          >
                            {sec.letter}
                          </button>
                          <div>
                            <h2 className="font-serif-editorial text-2xl font-bold text-[#1A1817] leading-none">
                              <button
                                type="button"
                                onClick={() => handleOpenLetterSection(sec.letter)}
                                className="hover:text-[#9E3B24] transition-colors cursor-pointer"
                              >
                                Раздел «{sec.letter}»
                              </button>
                            </h2>
                            <span className="font-mono-archival text-xs text-[#7A7167]">
                              {sec.url} · {sec.count} форм выставок
                            </span>
                          </div>
                        </div>

                        <button
                          type="button"
                          onClick={() => handleOpenLetterSection(sec.letter)}
                          className="text-xs font-semibold text-[#9E3B24] hover:underline flex items-center gap-1 cursor-pointer"
                        >
                          <span>Открыть раздел</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      <ul className="space-y-2">
                        {sec.sampleTerms.map((term) => (
                          <li key={term.slug}>
                            <a
                              href={`/glossary/exhibitions/${term.slug}/`}
                              onClick={(e) => {
                                e.preventDefault();
                                handleOpenExhibitionBySlug(term.slug, sec.letter);
                              }}
                              className="group flex items-center justify-between gap-2 py-1.5 px-2.5 rounded-lg hover:bg-[#FAF6F0] text-sm text-[#1A1817] no-underline transition-colors"
                            >
                              <span className="group-hover:text-[#9E3B24] font-medium transition-colors">
                                {term.title}
                              </span>
                              <span className="flex items-center gap-1.5 shrink-0">
                                {term.hasPhoto && (
                                  <span className="inline-flex items-center gap-0.5 text-[10px] font-mono-archival px-1.5 py-0.5 rounded bg-[#F3ECE2] text-[#4A443F]">
                                    <Camera className="w-2.5 h-2.5 text-[#9E3B24]" /> Фото
                                  </span>
                                )}
                                {term.isNew && (
                                  <span className="text-[10px] font-mono-archival px-1.5 py-0.5 rounded bg-[#2E5A44]/10 text-[#2E5A44]">
                                    +Новое
                                  </span>
                                )}
                                <ChevronRight className="w-3.5 h-3.5 text-[#C5B9A8] group-hover:text-[#9E3B24] group-hover:translate-x-0.5 transition-all" />
                              </span>
                            </a>
                          </li>
                        ))}
                      </ul>
                    </section>
                  ))}
                </div>
              </div>
            )}

            {/* =========================================================
                PAGE 3: LETTER SECTION VIEW (_layouts/section.html)
               ========================================================= */}
            {sitePage === 'section' && (
              <div className="space-y-8">
                {/* Breadcrumbs (_includes/breadcrumbs.html) */}
                <nav className="flex items-center gap-2 text-xs text-[#7A7167]">
                  <button
                    type="button"
                    onClick={() => setSitePage('home')}
                    className="hover:text-[#9E3B24] cursor-pointer"
                  >
                    Главная
                  </button>
                  <ChevronRight className="w-3.5 h-3.5" />
                  <button
                    type="button"
                    onClick={() => setSitePage('contents')}
                    className="hover:text-[#9E3B24] cursor-pointer"
                  >
                    Указатель
                  </button>
                  <ChevronRight className="w-3.5 h-3.5" />
                  <span className="text-[#1A1817] font-medium">
                    Раздел «{currentLetterObj.letter}»
                  </span>
                </nav>

                {/* Section Header Banner */}
                <div className="relative rounded-3xl border border-[#E2D9CC] bg-white p-6 sm:p-8 overflow-hidden flex flex-col sm:flex-row sm:items-center justify-between gap-6">
                  <div className="flex items-center gap-5">
                    <div className="w-20 h-20 rounded-2xl bg-[#9E3B24] text-white font-serif-editorial text-5xl font-bold flex items-center justify-center shadow-md shrink-0">
                      {currentLetterObj.letter}
                    </div>
                    <div>
                      <div className="font-mono-archival text-xs text-[#7A7167] uppercase">
                        КОЛЛЕКЦИЯ _SECTIONS · {currentLetterObj.url}
                      </div>
                      <h1 className="font-serif-editorial text-3xl sm:text-4xl font-bold text-[#1A1817]">
                        Раздел «{currentLetterObj.letter}»
                      </h1>
                      <p className="text-sm text-[#4A443F] mt-1">
                        Выставок в разделе: <strong>{currentLetterObj.count}</strong>. Полные описания — на отдельных страницах.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Alphabet Navigator with active letter highlighted */}
                <AlphabetNavigator
                  activeLetter={currentLetterObj.letter}
                  onSelectLetter={handleOpenLetterSection}
                  onSelectExhibitionSlug={handleOpenExhibitionBySlug}
                  compactHeader
                />

                {/* Cards for this Letter */}
                <div className="space-y-4">
                  <h2 className="font-serif-editorial text-2xl font-bold text-[#1A1817]">
                    Карточки выставок на букву «{currentLetterObj.letter}»
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {EXHIBITIONS_DATA.filter(
                      (item) => item.letter === currentLetterObj.letter
                    ).map((item) => (
                      <CatalogCard
                        key={item.id}
                        item={item}
                        onSelect={handleOpenExhibition}
                        onSelectLetter={handleOpenLetterSection}
                      />
                    ))}

                    {/* Also render remaining sampleTerms of this letter as interactive cards */}
                    {currentLetterObj.sampleTerms
                      .filter(
                        (t) => !EXHIBITIONS_DATA.some((e) => e.slug === t.slug)
                      )
                      .map((term, idx) => (
                        <div
                          key={term.slug}
                          onClick={() =>
                            handleOpenExhibitionBySlug(
                              term.slug,
                              currentLetterObj.letter
                            )
                          }
                          className="spotlight-card group rounded-2xl border border-[#E2D9CC] bg-white p-5 flex flex-col justify-between cursor-pointer"
                        >
                          <div>
                            <div className="flex items-center justify-between pb-3 mb-3 border-b border-dashed border-[#E2D9CC]">
                              <span className="font-mono-archival text-xs text-[#7A7167]">
                                РАЗДЕЛ «{currentLetterObj.letter}» · № {idx + 5}
                              </span>
                              {term.hasPhoto && (
                                <span className="inline-flex items-center gap-1 text-[10px] font-mono-archival px-2 py-0.5 rounded-full bg-[#F3ECE2] text-[#4A443F]">
                                  <Camera className="w-3 h-3 text-[#9E3B24]" /> Фото
                                </span>
                              )}
                            </div>
                            <h3 className="font-serif-editorial text-2xl font-bold text-[#1A1817] group-hover:text-[#9E3B24] transition-colors">
                              {term.title}
                            </h3>
                            <p className="text-xs sm:text-sm text-[#4A443F] mt-2">
                              Статья из коллекции{' '}
                              <code className="font-mono-archival text-xs">
                                _exhibitions/{term.slug}.html
                              </code>
                              . Нажмите, чтобы открыть полный макет страницы термина.
                            </p>
                          </div>
                          <div className="pt-3 mt-4 border-t border-[#E2D9CC] flex items-center justify-between text-xs font-semibold text-[#9E3B24]">
                            <span>/glossary/exhibitions/{term.slug}/</span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              </div>
            )}

            {/* =========================================================
                PAGE 4: EXHIBITION ARTICLE (_layouts/exhibition.html)
               ========================================================= */}
            {sitePage === 'exhibition' && (
              <div className="max-w-4xl mx-auto space-y-8">
                {/* Breadcrumbs (_includes/breadcrumbs.html) */}
                <nav className="flex flex-wrap items-center gap-2 text-xs text-[#7A7167]">
                  <button
                    type="button"
                    onClick={() => setSitePage('home')}
                    className="hover:text-[#9E3B24] cursor-pointer"
                  >
                    Главная
                  </button>
                  <ChevronRight className="w-3.5 h-3.5" />
                  <button
                    type="button"
                    onClick={() => setSitePage('contents')}
                    className="hover:text-[#9E3B24] cursor-pointer"
                  >
                    Указатель
                  </button>
                  <ChevronRight className="w-3.5 h-3.5" />
                  <button
                    type="button"
                    onClick={() =>
                      handleOpenLetterSection(selectedExhibition.letter)
                    }
                    className="hover:text-[#9E3B24] cursor-pointer"
                  >
                    Раздел «{selectedExhibition.letter}»
                  </button>
                  <ChevronRight className="w-3.5 h-3.5" />
                  <span className="text-[#1A1817] font-medium">
                    {selectedExhibition.title}
                  </span>
                </nav>

                {/* Main Archival Exhibition Card */}
                <article className="rounded-3xl border border-[#E2D9CC] bg-white p-6 sm:p-10 shadow-sm space-y-6">
                  {/* Top Metadata Passport Bar */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-dashed border-[#E2D9CC]">
                    <div className="flex items-center gap-2.5">
                      <button
                        type="button"
                        onClick={() =>
                          handleOpenLetterSection(selectedExhibition.letter)
                        }
                        className="w-9 h-9 rounded-xl bg-[#9E3B24] text-white font-serif-editorial font-bold text-xl flex items-center justify-center cursor-pointer"
                      >
                        {selectedExhibition.letter}
                      </button>
                      <div>
                        <span className="font-mono-archival text-xs uppercase text-[#7A7167] block">
                          КАТАЛОЖНАЯ КАРТОЧКА № {String(selectedExhibition.order).padStart(3, '0')}
                        </span>
                        <code className="font-mono-archival text-xs text-[#9E3B24]">
                          {selectedExhibition.url}
                        </code>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      <span className="px-3 py-1 rounded-full text-xs font-medium bg-[#FAF6F0] border border-[#E2D9CC] text-[#4A443F]">
                        {selectedExhibition.category}
                      </span>
                      <span className="px-3 py-1 rounded-full text-xs font-medium bg-[#F3ECE2] text-[#1A1817]">
                        {selectedExhibition.audience}
                      </span>
                      <button
                        type="button"
                        onClick={() => {
                          navigator.clipboard.writeText(
                            `${selectedExhibition.title} — ${selectedExhibition.definition} («Книга – Выставка – Читатель», ЦГДБ г. Уфы)`
                          );
                          setCopiedCitation(true);
                          setTimeout(() => setCopiedCitation(false), 2000);
                        }}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono-archival bg-[#9E3B24]/10 text-[#9E3B24] hover:bg-[#9E3B24] hover:text-white transition-colors cursor-pointer"
                      >
                        {copiedCitation ? (
                          <>
                            <Check className="w-3.5 h-3.5" />
                            <span>Цитата скопирована</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5" />
                            <span>Цитировать</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Title */}
                  <h1 className="font-serif-editorial text-3xl sm:text-5xl font-bold text-[#1A1817] leading-tight">
                    {selectedExhibition.title}
                  </h1>

                  {/* Definition with Drop Cap */}
                  <p className="text-base sm:text-lg text-[#1A1817] leading-relaxed editorial-dropcap">
                    {selectedExhibition.definition}
                  </p>

                  {/* Practical Example Callout Box */}
                  {selectedExhibition.example && (
                    <div className="rounded-2xl bg-[#FAF6F0] border-l-4 border-[#9E3B24] p-5 space-y-1.5">
                      <div className="font-mono-archival text-xs uppercase tracking-wider text-[#9E3B24] font-semibold">
                        Методический пример из практики библиотек:
                      </div>
                      <p className="text-sm sm:text-base text-[#4A443F] leading-relaxed m-0">
                        {selectedExhibition.example}
                      </p>
                      {selectedExhibition.sourceNote && (
                        <div className="text-xs text-[#7A7167] italic pt-1">
                          Источник: {selectedExhibition.sourceNote}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Museum Polaroid Photo Frame (if exhibition has photo in repo) */}
                  {selectedExhibition.imageUrl && (
                    <figure className="rounded-2xl bg-[#FAF6F0] border border-[#E2D9CC] p-4 sm:p-6 text-center shadow-inner">
                      <div className="overflow-hidden rounded-xl border border-[#E2D9CC] bg-white max-h-[420px] flex items-center justify-center">
                        <img
                          src={selectedExhibition.imageUrl}
                          alt={selectedExhibition.title}
                          className="max-h-[400px] w-auto object-contain mx-auto"
                        />
                      </div>
                      <figcaption className="mt-3 text-xs sm:text-sm text-[#7A7167] font-serif-editorial italic flex items-center justify-center gap-2">
                        <Camera className="w-4 h-4 text-[#9E3B24]" />
                        <span>
                          {selectedExhibition.imageCaption ||
                            `Фото-пример оформления: ${selectedExhibition.title} (из архива ЦГДБ г. Уфы)`}
                        </span>
                      </figcaption>
                    </figure>
                  )}

                  {/* Recommended Accessories Strip */}
                  <div className="pt-4 border-t border-[#E2D9CC] flex flex-wrap items-center justify-between gap-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-mono-archival uppercase text-[#7A7167]">
                        Рекомендуемые аксессуары:
                      </span>
                      {selectedExhibition.accessories.map((acc) => (
                        <span
                          key={acc}
                          className="text-xs px-3 py-1 rounded-lg bg-[#F3ECE2] text-[#1A1817] font-medium"
                        >
                          {acc}
                        </span>
                      ))}
                    </div>
                  </div>
                </article>

                {/* Prev / Next Pager (_includes/pager.html) with Keyboard Hints */}
                <nav
                  aria-label="Переход между соседними выставками"
                  className="grid grid-cols-1 sm:grid-cols-2 gap-4"
                >
                  {prevExhibition ? (
                    <button
                      type="button"
                      onClick={() => handleOpenExhibition(prevExhibition)}
                      className="text-left p-4 rounded-2xl border border-[#E2D9CC] bg-white hover:border-[#9E3B24] transition-all flex items-center gap-3 group cursor-pointer"
                    >
                      <ArrowLeft className="w-5 h-5 text-[#7A7167] group-hover:text-[#9E3B24] group-hover:-translate-x-1 transition-all shrink-0" />
                      <div>
                        <span className="font-mono-archival text-[11px] text-[#7A7167] block">
                          ← Предыдущая форма (Клавиша ←)
                        </span>
                        <span className="font-serif-editorial text-lg font-bold text-[#1A1817] group-hover:text-[#9E3B24]">
                          {prevExhibition.title}
                        </span>
                      </div>
                    </button>
                  ) : (
                    <div />
                  )}

                  {nextExhibition && (
                    <button
                      type="button"
                      onClick={() => handleOpenExhibition(nextExhibition)}
                      className="text-right p-4 rounded-2xl border border-[#E2D9CC] bg-white hover:border-[#9E3B24] transition-all flex items-center justify-end gap-3 group cursor-pointer"
                    >
                      <div>
                        <span className="font-mono-archival text-[11px] text-[#7A7167] block">
                          Следующая форма (Клавиша →) →
                        </span>
                        <span className="font-serif-editorial text-lg font-bold text-[#1A1817] group-hover:text-[#9E3B24]">
                          {nextExhibition.title}
                        </span>
                      </div>
                      <ArrowRight className="w-5 h-5 text-[#7A7167] group-hover:text-[#9E3B24] group-hover:translate-x-1 transition-all shrink-0" />
                    </button>
                  )}
                </nav>
              </div>
            )}

            {/* =========================================================
                PAGE 5: CONCLUSION (site/conclusion/index.html)
               ========================================================= */}
            {sitePage === 'conclusion' && (
              <div className="max-w-3xl mx-auto space-y-8">
                <article className="rounded-3xl border border-[#E2D9CC] bg-white p-6 sm:p-10 shadow-sm space-y-6">
                  <div className="font-mono-archival text-xs uppercase tracking-wider text-[#9E3B24]">
                    ЗАКЛЮЧЕНИЕ · КОЛЛЕКТИВ АВТОРОВ ЦСДБ ГО Г. УФА
                  </div>
                  <h1 className="font-serif-editorial text-4xl sm:text-5xl font-bold text-[#1A1817]">
                    Заключение
                  </h1>
                  <p className="text-base sm:text-lg text-[#4A443F] leading-relaxed editorial-dropcap">
                    В данном глоссарии мы постарались не только рассмотреть наиболее актуальные вопросы организации выставочной работы в детских библиотеках, но и подробнее познакомить Вас с нестандартными формами книжных выставок, которые были разработаны коллегами из детских библиотек Российской Федерации, Республики Башкортостан, Централизованной системы детских библиотек городского округа г. Уфа.
                  </p>
                  <p className="text-base text-[#4A443F] leading-relaxed">
                    Подобные приемы организации выставок помогают вызвать максимальный интерес к книгам, а также другим документам, которые на них представлены, создать целостный, привлекательный, действенный, эффективный образ выставок, усилить их педагогический, информационный, эстетический и познавательный потенциал.
                  </p>

                  {/* Official Contact Stamp Card */}
                  <div className="rounded-2xl bg-[#FAF6F0] border border-[#E2D9CC] p-6 space-y-3">
                    <h2 className="font-serif-editorial text-2xl font-bold text-[#1A1817]">
                      Приглашаем коллег к соавторству и пополнению глоссария
                    </h2>
                    <p className="text-sm text-[#4A443F]">
                      Присылайте нам информацию о Вашем опыте в создании нетрадиционных выставок, и мы с удовольствием пополним наш глоссарий:
                    </p>
                    <div className="flex flex-wrap gap-4 pt-2 text-sm">
                      <div className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white border border-[#E2D9CC] text-[#1A1817]">
                        <MapPin className="w-4 h-4 text-[#9E3B24]" />
                        <span>МБУ «Централизованная система детских библиотек» ГО г. Уфа РБ г. Уфа, 450078, ул. Мингажева, 109</span>
                      </div>
                      <a
                        href="mailto:ufacsdb@yandex.ru"
                        className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#9E3B24] text-white font-semibold no-underline hover:bg-[#B8462B] transition-colors"
                      >
                        <Mail className="w-4 h-4" />
                        <span>ufacsdb@yandex.ru</span>
                      </a>
                    </div>
                  </div>
                </article>
              </div>
            )}
          </main>

          {/* REDESIGNED SITE FOOTER (_includes/footer.html) */}
          <footer className="border-t border-[#E2D9CC] bg-white mt-14">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-xs text-[#7A7167]">
              <div className="space-y-1">
                <p className="font-semibold text-[#1A1817]">
                  «Книга – Выставка – Читатель»: глоссарий нетрадиционных форм книжных выставок.
                </p>
                <p>
                  <a href="https://cgdb.ufacsdb.ru/" />МБУ «Централизованная система детских библиотек» ГО г. Уфа РБ
                </p>
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setWorkspaceTab('agent-plan')}
                  className="px-3.5 py-2 rounded-xl bg-[#FAF6F0] hover:bg-[#F3ECE2] text-[#9E3B24] border border-[#E2D9CC] font-semibold cursor-pointer"
                >
                  Открыть ТЗ и код для ИИ-агента →
                </button>
              </div>
            </div>
          </footer>
        </div>
      )}

      {/* COMMAND PALETTE MODAL (⌘K) */}
      <CommandPaletteModal
        isOpen={isCmdkOpen}
        onClose={() => setIsCmdkOpen(false)}
        onSelectExhibition={handleOpenExhibition}
        onSelectLetter={handleOpenLetterSection}
      />
    </div>
  );
}

export default App;
