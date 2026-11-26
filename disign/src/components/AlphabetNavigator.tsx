import React, { useState, useRef } from 'react';
import {
  ALL_CYRILLIC_LETTERS,
  AlphabetLetterInfo,
} from '../data/glossaryData';
import {
  ArrowUpRight,
  Sparkles,
  Camera,
  Layers,
  Eye,
  Compass,
  SlidersHorizontal,
  ExternalLink,
} from 'lucide-react';

export type AlphabetVisualMode = 'matrix' | 'magnetic' | 'compact';

interface AlphabetNavigatorProps {
  activeLetter: string | null;
  onSelectLetter: (letter: string) => void;
  onSelectExhibitionSlug: (slug: string, letter: string) => void;
  onOpenFullIndex?: () => void;
  defaultMode?: AlphabetVisualMode;
  compactHeader?: boolean;
}

export const AlphabetNavigator: React.FC<AlphabetNavigatorProps> = ({
  activeLetter,
  onSelectLetter,
  onSelectExhibitionSlug,
  onOpenFullIndex,
  defaultMode = 'matrix',
  compactHeader = false,
}) => {
  const [visualMode, setVisualMode] = useState<AlphabetVisualMode>(defaultMode);
  const [hideInactive, setHideInactive] = useState<boolean>(false);
  const [hoveredLetter, setHoveredLetter] = useState<AlphabetLetterInfo | null>(
    ALL_CYRILLIC_LETTERS[0]
  );

  // Magnetic dock cursor X tracking (Designer JS/TS Physics)
  const dockRef = useRef<HTMLDivElement | null>(null);
  const letterRefs = useRef<Record<string, HTMLAnchorElement | HTMLSpanElement | null>>({});
  const [mouseX, setMouseX] = useState<number | null>(null);

  const visibleLetters = hideInactive
    ? ALL_CYRILLIC_LETTERS.filter((item) => item.active)
    : ALL_CYRILLIC_LETTERS;

  const maxCount = Math.max(...ALL_CYRILLIC_LETTERS.map((l) => l.count));

  const getMagneticStyle = (letterKey: string, isActive: boolean): React.CSSProperties => {
    if (visualMode !== 'magnetic' || mouseX === null) {
      return {};
    }
    const el = letterRefs.current[letterKey];
    if (!el || !dockRef.current) return {};
    const rect = el.getBoundingClientRect();
    const dockRect = dockRef.current.getBoundingClientRect();
    const center = rect.left - dockRect.left + rect.width / 2;
    const distance = Math.abs(mouseX - center);
    const radius = 135;

    if (distance > radius) {
      return {
        transform: 'translateY(0px) scale(1)',
        transition: 'transform 180ms cubic-bezier(0.22, 1, 0.36, 1)',
      };
    }

    // Smooth cosine wave falloff loved by UI designers
    const normalized = (1 + Math.cos((Math.PI * distance) / radius)) / 2;
    const scale = isActive ? 1 + normalized * 0.36 : 1 + normalized * 0.12;
    const lift = isActive ? -normalized * 9 : -normalized * 2;

    return {
      transform: `translateY(${lift.toFixed(1)}px) scale(${scale.toFixed(3)})`,
      zIndex: Math.round(normalized * 20) + 2,
      transition: 'transform 60ms linear',
    };
  };

  const previewTarget =
    hoveredLetter ||
    ALL_CYRILLIC_LETTERS.find((l) => l.letter === activeLetter) ||
    ALL_CYRILLIC_LETTERS[0];

  return (
    <section
      aria-label="Алфавитный указатель от А до Я"
      className="relative rounded-2xl border border-[#E2D9CC] bg-[#FFFFFF]/90 p-5 sm:p-6 shadow-[0_12px_36px_-16px_rgba(26,24,23,0.08)] backdrop-blur-md"
    >
      {/* Top Control Bar: Title + Designer Mode Switcher */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 mb-5 border-b border-[#E2D9CC]">
        <div className="flex items-start sm:items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#9E3B24]/10 border border-[#9E3B24]/25 flex items-center justify-center text-[#9E3B24] shrink-0 font-serif-editorial font-bold text-xl">
            А–Я
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="font-serif-editorial text-xl sm:text-2xl font-bold text-[#1A1817] tracking-tight m-0">
                Интерактивный алфавитный указатель с быстрыми ссылками
              </h2>
              <span className="font-mono-archival text-[11px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#F3ECE2] text-[#7A7167] border border-[#E2D9CC]">
                27 разделов · 271 выставка
              </span>
            </div>
            {!compactHeader && (
              <p className="text-xs sm:text-sm text-[#7A7167] mt-0.5">
                Наведите на любую букву для мгновенного предпросмотра ссылок раздела или кликните для фильтрации (`_includes/letter-nav.html`)
              </p>
            )}
          </div>
        </div>

        {/* Mode Selector Pills */}
        <div className="flex flex-wrap items-center gap-2">
          <div
            className="inline-flex rounded-xl bg-[#F3ECE2] p-1 border border-[#E2D9CC]"
            role="group"
            aria-label="Режим отображения алфавита"
          >
            <button
              type="button"
              onClick={() => setVisualMode('matrix')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                visualMode === 'matrix'
                  ? 'bg-[#FFFFFF] text-[#9E3B24] shadow-xs font-semibold'
                  : 'text-[#4A443F] hover:text-[#1A1817]'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Матрица + Превью</span>
            </button>
            <button
              type="button"
              onClick={() => setVisualMode('magnetic')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                visualMode === 'magnetic'
                  ? 'bg-[#FFFFFF] text-[#9E3B24] shadow-xs font-semibold'
                  : 'text-[#4A443F] hover:text-[#1A1817]'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Магнитный док (JS)</span>
            </button>
            <button
              type="button"
              onClick={() => setVisualMode('compact')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                visualMode === 'compact'
                  ? 'bg-[#FFFFFF] text-[#9E3B24] shadow-xs font-semibold'
                  : 'text-[#4A443F] hover:text-[#1A1817]'
              }`}
            >
              <Compass className="w-3.5 h-3.5" />
              <span>Тепловая лента</span>
            </button>
          </div>

          <button
            type="button"
            onClick={() => setHideInactive((prev) => !prev)}
            title="Скрыть или показать 6 неактивных букв (Ё, Й, Щ, Ъ, Ы, Ь)"
            className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border transition-all cursor-pointer ${
              hideInactive
                ? 'bg-[#9E3B24]/10 border-[#9E3B24]/30 text-[#9E3B24]'
                : 'bg-[#FAF6F0] border-[#E2D9CC] text-[#4A443F] hover:border-[#C5B9A8]'
            }`}
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>{hideInactive ? 'Только 27 активных' : 'Все 33 буквы'}</span>
          </button>
        </div>
      </div>

      {/* ALPHABET RENDERING BY MODE */}
      <div
        ref={dockRef}
        onMouseMove={(e) => {
          if (visualMode === 'magnetic' && dockRef.current) {
            const rect = dockRef.current.getBoundingClientRect();
            setMouseX(e.clientX - rect.left);
          }
        }}
        onMouseLeave={() => setMouseX(null)}
        className={
          visualMode === 'matrix'
            ? 'grid grid-cols-6 sm:grid-cols-9 md:grid-cols-11 gap-2'
            : visualMode === 'magnetic'
            ? 'flex flex-wrap items-center justify-center gap-1.5 sm:gap-2 py-3 px-2 rounded-xl bg-[#FAF6F0]/90 border border-[#E2D9CC]'
            : 'flex flex-wrap items-center gap-1.5'
        }
      >
        {visibleLetters.map((item) => {
          const isSelected = activeLetter === item.letter;
          const isHovered = previewTarget?.letter === item.letter;
          const densityPercent = Math.max(12, Math.round((item.count / maxCount) * 100));

          if (!item.active) {
            return (
              <span
                key={item.letter}
                ref={(el) => {
                  letterRefs.current[item.letter] = el;
                }}
                style={getMagneticStyle(item.letter, false)}
                title={`На букву «${item.letter}» в словаре нет терминов`}
                aria-disabled="true"
                className={`inactive-letter-hatch select-none flex flex-col items-center justify-center rounded-xl border border-dashed border-[#E2D9CC] text-[#C5BCB0] cursor-not-allowed ${
                  visualMode === 'matrix'
                    ? 'h-16 p-2'
                    : visualMode === 'magnetic'
                    ? 'w-10 h-12 text-base'
                    : 'w-9 h-9 text-sm'
                }`}
              >
                <span className="font-serif-editorial text-lg font-medium leading-none">
                  {item.letter}
                </span>
                {visualMode === 'matrix' && (
                  <span className="font-mono-archival text-[10px] mt-1 opacity-60">—</span>
                )}
              </span>
            );
          }

          return (
            <a
              key={item.letter}
              href={`#section-${item.slug}`}
              ref={(el) => {
                letterRefs.current[item.letter] = el;
              }}
              style={getMagneticStyle(item.letter, true)}
              onClick={(e) => {
                e.preventDefault();
                onSelectLetter(item.letter);
                setHoveredLetter(item);
              }}
              onMouseEnter={() => setHoveredLetter(item)}
              onFocus={() => setHoveredLetter(item)}
              aria-current={isSelected ? 'page' : undefined}
              className={`group relative flex flex-col items-center justify-between rounded-xl border transition-all no-underline cursor-pointer ${
                visualMode === 'matrix'
                  ? 'h-16 p-2'
                  : visualMode === 'magnetic'
                  ? 'w-11 h-14 p-1.5 shadow-xs'
                  : 'px-3 py-1.5 flex-row gap-1.5'
              } ${
                isSelected
                  ? 'bg-[#9E3B24] text-[#FFFFFF] border-[#9E3B24] shadow-[0_8px_20px_-6px_rgba(158,59,36,0.45)]'
                  : isHovered
                  ? 'bg-[#FAF6F0] text-[#9E3B24] border-[#9E3B24]/60 shadow-sm'
                  : 'bg-[#FFFFFF] text-[#1A1817] border-[#E2D9CC] hover:border-[#9E3B24]/50 hover:bg-[#FAF6F0]'
              }`}
            >
              {/* Top corner subtle dot if section has many items */}
              {item.count >= 15 && visualMode === 'matrix' && (
                <span
                  title="Крупный раздел (15+ форм выставок)"
                  className={`absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full ${
                    isSelected ? 'bg-[#FFFFFF]' : 'bg-[#C88A32]'
                  }`}
                />
              )}

              <span
                className={`font-serif-editorial font-bold leading-none tracking-tight ${
                  visualMode === 'matrix'
                    ? 'text-2xl mt-0.5'
                    : visualMode === 'magnetic'
                    ? 'text-xl mt-0.5'
                    : 'text-lg'
                }`}
              >
                {item.letter}
              </span>

              {/* Count badge */}
              <span
                className={`font-mono-archival text-[10px] leading-none ${
                  isSelected
                    ? 'text-[#FFFFFF]/90'
                    : 'text-[#7A7167] group-hover:text-[#9E3B24]'
                }`}
              >
                {item.count}
              </span>

              {/* Density micro-bar at bottom of tile */}
              {(visualMode === 'matrix' || visualMode === 'compact') && (
                <span className="w-full h-1 rounded-full bg-[#E2D9CC]/60 overflow-hidden mt-0.5">
                  <span
                    className={`block h-full rounded-full transition-all duration-300 ${
                      isSelected ? 'bg-[#FFFFFF]' : 'bg-[#9E3B24]/75'
                    }`}
                    style={{ width: `${densityPercent}%` }}
                  />
                </span>
              )}
            </a>
          );
        })}
      </div>

      {/* LIVE HOVER / SELECTED SECTION PREVIEW BAR WITH DIRECT LINKS */}
      {previewTarget && previewTarget.active && (
        <div className="mt-5 pt-4 border-t border-[#E2D9CC] bg-[#FAF6F0]/80 -mx-5 sm:-mx-6 -mb-5 sm:-mb-6 p-5 sm:p-6 rounded-b-2xl">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-xl bg-[#9E3B24] text-white flex items-center justify-center font-serif-editorial text-2xl font-bold shadow-xs">
                {previewTarget.letter}
              </div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-serif-editorial font-bold text-lg text-[#1A1817]">
                    Раздел «{previewTarget.letter}»
                  </span>
                  <code className="font-mono-archival text-xs px-2 py-0.5 rounded bg-[#F3ECE2] text-[#9E3B24] border border-[#E2D9CC]">
                    {previewTarget.url}
                  </code>
                  <span className="text-xs text-[#7A7167]">
                    · {previewTarget.count} форм выставок в разделе
                  </span>
                </div>
                <p className="text-xs text-[#4A443F] mt-0.5">
                  Быстрые ссылки на термины буквы «{previewTarget.letter}» (кликните по ссылке, чтобы открыть статью выставки):
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                type="button"
                onClick={() => onSelectLetter(previewTarget.letter)}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#9E3B24] hover:bg-[#B8462B] text-white text-xs font-semibold transition-all shadow-xs cursor-pointer"
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Все выставки на «{previewTarget.letter}» ({previewTarget.count})</span>
              </button>
              {onOpenFullIndex && (
                <button
                  type="button"
                  onClick={onOpenFullIndex}
                  className="inline-flex items-center gap-1 px-3 py-2 rounded-xl bg-white hover:bg-[#F3ECE2] text-[#1A1817] border border-[#E2D9CC] text-xs font-medium transition-all cursor-pointer"
                >
                  <span>Весь указатель</span>
                  <ArrowUpRight className="w-3.5 h-3.5 text-[#9E3B24]" />
                </button>
              )}
            </div>
          </div>

          {/* Direct Links Pill Cloud for the Hovered/Active Letter */}
          <div className="flex flex-wrap gap-2 mt-3">
            {previewTarget.sampleTerms.map((term) => (
              <a
                key={term.slug}
                href={`/glossary/exhibitions/${term.slug}/`}
                onClick={(e) => {
                  e.preventDefault();
                  onSelectExhibitionSlug(term.slug, previewTarget.letter);
                }}
                className="group inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white border border-[#E2D9CC] hover:border-[#9E3B24] hover:bg-[#9E3B24]/[0.04] text-xs sm:text-sm text-[#1A1817] transition-all no-underline shadow-[0_1px_2px_rgba(0,0,0,0.03)]"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-[#9E3B24]/50 group-hover:bg-[#9E3B24] transition-colors" />
                <span className="font-medium group-hover:text-[#9E3B24] transition-colors">
                  {term.title}
                </span>
                {term.hasPhoto && (
                  <span
                    title="В статье есть фото-пример из библиотеки"
                    className="inline-flex items-center gap-0.5 text-[10px] font-mono-archival px-1.5 py-0.5 rounded bg-[#F3ECE2] text-[#4A443F]"
                  >
                    <Camera className="w-2.5 h-2.5 text-[#9E3B24]" />
                    Фото
                  </span>
                )}
                {term.isNew && (
                  <span
                    title="Входит в 72 новые формы 2-го издания"
                    className="text-[10px] font-mono-archival px-1.5 py-0.5 rounded bg-[#2E5A44]/10 text-[#2E5A44] font-medium"
                  >
                    +Новое
                  </span>
                )}
                <ExternalLink className="w-3 h-3 text-[#7A7167] opacity-0 group-hover:opacity-100 transition-opacity" />
              </a>
            ))}
          </div>
        </div>
      )}
    </section>
  );
};
