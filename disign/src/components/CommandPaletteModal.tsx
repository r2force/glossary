import React, { useState, useEffect, useRef } from 'react';
import {
  ALL_CYRILLIC_LETTERS,
  EXHIBITIONS_DATA,
  ExhibitionItem,
} from '../data/glossaryData';
import {
  Search,
  X,
  Shuffle,
  Camera,
  Sparkles,
  ArrowRight,
  CornerDownLeft,
} from 'lucide-react';

interface CommandPaletteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectExhibition: (item: ExhibitionItem) => void;
  onSelectLetter: (letter: string) => void;
}

export const CommandPaletteModal: React.FC<CommandPaletteModalProps> = ({
  isOpen,
  onClose,
  onSelectExhibition,
  onSelectLetter,
}) => {
  const [query, setQuery] = useState('');
  const [onlyPhotos, setOnlyPhotos] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery('');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const q = query.trim().toLowerCase();

  // Match detailed exhibitions
  const matchedExhibitions = EXHIBITIONS_DATA.filter((item) => {
    if (onlyPhotos && !item.imageUrl) return false;
    if (!q) return true;
    return (
      item.title.toLowerCase().includes(q) ||
      item.definition.toLowerCase().includes(q) ||
      item.category.toLowerCase().includes(q) ||
      item.accessories.some((a) => a.toLowerCase().includes(q)) ||
      item.letter.toLowerCase() === q
    );
  });

  // Also match sample terms across all 27 letters from ALL_CYRILLIC_LETTERS
  const matchedSampleLinks = q
    ? ALL_CYRILLIC_LETTERS.filter((l) => l.active).flatMap((l) =>
        l.sampleTerms
          .filter((t) => t.title.toLowerCase().includes(q))
          .map((t) => ({ ...t, letter: l.letter }))
      )
    : [];

  const handleRandomPick = () => {
    const randomItem =
      EXHIBITIONS_DATA[Math.floor(Math.random() * EXHIBITIONS_DATA.length)];
    onSelectExhibition(randomItem);
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-14 sm:pt-20 px-4 bg-[#1A1817]/55 backdrop-blur-xs"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl rounded-2xl border border-[#C5B9A8] bg-[#FAF6F0] shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Search Input */}
        <div className="flex items-center gap-3 px-4 py-3.5 bg-white border-b border-[#E2D9CC]">
          <Search className="w-5 h-5 text-[#9E3B24] shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Поиск по 271 форме выставок, аксессуарам или букве (например: ай-стоппер, игра, буккроссинг)…"
            className="w-full bg-transparent text-sm sm:text-base text-[#1A1817] placeholder:text-[#7A7167] focus:outline-none"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="text-xs text-[#7A7167] hover:text-[#1A1817] cursor-pointer"
            >
              Очистить
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-[#F3ECE2] text-[#7A7167] cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Filter & Random Action Bar */}
        <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 bg-[#F3ECE2]/70 border-b border-[#E2D9CC] text-xs">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setOnlyPhotos((v) => !v)}
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border transition-colors cursor-pointer ${
                onlyPhotos
                  ? 'bg-[#9E3B24] text-white border-[#9E3B24]'
                  : 'bg-white text-[#4A443F] border-[#E2D9CC]'
              }`}
            >
              <Camera className="w-3.5 h-3.5" />
              <span>Только с фото-примерами</span>
            </button>
            <span className="text-[#7A7167] hidden sm:inline">
              Индекс: <code className="font-mono-archival">/search-index.json</code>
            </span>
          </div>

          <button
            type="button"
            onClick={handleRandomPick}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-[#C88A32]/15 hover:bg-[#C88A32]/25 text-[#9E3B24] font-semibold transition-colors cursor-pointer"
          >
            <Shuffle className="w-3.5 h-3.5" />
            <span>Случайная идея выставки</span>
          </button>
        </div>

        {/* Quick Alphabet Jump Strip inside Modal */}
        <div className="px-4 py-2.5 bg-white/60 border-b border-[#E2D9CC] flex items-center gap-1 overflow-x-auto">
          <span className="text-[11px] font-mono-archival text-[#7A7167] mr-1 shrink-0">
            Буква:
          </span>
          {ALL_CYRILLIC_LETTERS.filter((l) => l.active).map((l) => (
            <button
              key={l.letter}
              type="button"
              onClick={() => {
                onSelectLetter(l.letter);
                onClose();
              }}
              className="w-6 h-6 rounded bg-[#F3ECE2] hover:bg-[#9E3B24] text-[#1A1817] hover:text-white font-serif-editorial font-bold text-xs shrink-0 transition-colors cursor-pointer"
            >
              {l.letter}
            </button>
          ))}
        </div>

        {/* Results List */}
        <div className="max-h-96 overflow-y-auto p-3 space-y-2">
          {matchedExhibitions.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => {
                onSelectExhibition(item);
                onClose();
              }}
              className="w-full text-left p-3 rounded-xl bg-white hover:bg-[#FFFFFF] border border-[#E2D9CC] hover:border-[#9E3B24] flex items-start justify-between gap-3 transition-all group cursor-pointer"
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded bg-[#F3ECE2] text-[#9E3B24] font-serif-editorial font-bold text-xs flex items-center justify-center">
                    {item.letter}
                  </span>
                  <span className="font-serif-editorial font-bold text-lg text-[#1A1817] group-hover:text-[#9E3B24]">
                    {item.title}
                  </span>
                  {item.imageUrl && (
                    <span className="inline-flex items-center gap-0.5 text-[10px] font-mono-archival px-1.5 py-0.5 rounded bg-[#F3ECE2] text-[#4A443F]">
                      <Camera className="w-2.5 h-2.5 text-[#9E3B24]" /> Фото
                    </span>
                  )}
                  {item.isNewEdition && (
                    <span className="inline-flex items-center gap-0.5 text-[10px] font-mono-archival px-1.5 py-0.5 rounded bg-[#2E5A44]/10 text-[#2E5A44]">
                      <Sparkles className="w-2.5 h-2.5" /> +72
                    </span>
                  )}
                </div>
                <p className="text-xs text-[#4A443F] line-clamp-2 mt-1">
                  {item.definition}
                </p>
              </div>
              <span className="inline-flex items-center gap-1 text-xs font-mono-archival text-[#7A7167] group-hover:text-[#9E3B24] shrink-0 mt-1">
                <span>Открыть</span>
                <CornerDownLeft className="w-3.5 h-3.5" />
              </span>
            </button>
          ))}

          {/* Additional links from full alphabet index if not already in detailed list */}
          {matchedSampleLinks.length > 0 && (
            <div className="pt-2">
              <div className="text-[11px] font-mono-archival uppercase text-[#7A7167] px-2 mb-1.5">
                Ссылки из полного алфавитного указателя:
              </div>
              <div className="flex flex-wrap gap-1.5 px-1">
                {matchedSampleLinks.map((t) => (
                  <button
                    key={t.slug}
                    type="button"
                    onClick={() => {
                      onSelectLetter(t.letter);
                      onClose();
                    }}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white border border-[#E2D9CC] hover:border-[#9E3B24] text-xs text-[#1A1817] cursor-pointer"
                  >
                    <span className="font-bold text-[#9E3B24]">{t.letter}</span>
                    <span>{t.title}</span>
                    <ArrowRight className="w-3 h-3 text-[#7A7167]" />
                  </button>
                ))}
              </div>
            </div>
          )}

          {matchedExhibitions.length === 0 && matchedSampleLinks.length === 0 && (
            <div className="text-center py-8 text-sm text-[#7A7167]">
              По запросу «{query}» ничего не найдено. Попробуйте выбрать букву выше или нажать «Случайная идея выставки».
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
