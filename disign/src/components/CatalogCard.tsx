import React from 'react';
import { ExhibitionItem } from '../data/glossaryData';
import { ArrowUpRight, Camera, Sparkles, Bookmark } from 'lucide-react';

interface CatalogCardProps {
  item: ExhibitionItem;
  onSelect: (item: ExhibitionItem) => void;
  onSelectLetter?: (letter: string) => void;
}

export const CatalogCard: React.FC<CatalogCardProps> = ({
  item,
  onSelect,
  onSelectLetter,
}) => {
  const handleMouseMove = (e: React.MouseEvent<HTMLElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    e.currentTarget.style.setProperty('--mouse-x', `${x}px`);
    e.currentTarget.style.setProperty('--mouse-y', `${y}px`);
  };

  return (
    <article
      onMouseMove={handleMouseMove}
      onClick={() => onSelect(item)}
      className="spotlight-card group rounded-2xl border border-[#E2D9CC] bg-[#FFFFFF] p-5 flex flex-col justify-between cursor-pointer"
    >
      {/* Top Archival Index Strip */}
      <div>
        <div className="flex items-center justify-between gap-2 pb-3 mb-3 border-b border-dashed border-[#E2D9CC]">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onSelectLetter?.(item.letter);
              }}
              title={`Перейти в раздел буквы «${item.letter}»`}
              className="w-7 h-7 rounded-lg bg-[#F3ECE2] hover:bg-[#9E3B24] text-[#9E3B24] hover:text-white font-serif-editorial font-bold text-base flex items-center justify-center transition-colors cursor-pointer"
            >
              {item.letter}
            </button>
            <span className="font-mono-archival text-[11px] uppercase tracking-wider text-[#7A7167]">
              КАТ. № {String(item.order).padStart(3, '0')}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            {item.imageUrl && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono-archival bg-[#F3ECE2] text-[#4A443F] border border-[#E2D9CC]">
                <Camera className="w-3 h-3 text-[#9E3B24]" />
                Фото
              </span>
            )}
            {item.isNewEdition && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono-archival bg-[#2E5A44]/10 text-[#2E5A44] font-medium">
                <Sparkles className="w-2.5 h-2.5" />
                +72 Новая
              </span>
            )}
            {item.featured && (
              <span
                title="Избранная форма выставки на главной"
                className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] bg-[#C88A32]/15 text-[#9E3B24]"
              >
                <Bookmark className="w-3 h-3 fill-current" />
              </span>
            )}
          </div>
        </div>

        {/* Optional Thumbnail Banner if Photo Exists */}
        {item.imageUrl && (
          <div className="relative h-36 mb-3.5 rounded-xl overflow-hidden bg-[#F3ECE2] border border-[#E2D9CC]">
            <img
              src={item.imageUrl}
              alt={item.title}
              loading="lazy"
              className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-500"
              onError={(e) => {
                (e.currentTarget.parentElement as HTMLElement).style.display = 'none';
              }}
            />
            <div className="absolute inset-0 bg-gradient-to-t from-[#1A1817]/50 via-transparent to-transparent" />
            <span className="absolute bottom-2 left-2.5 right-2.5 text-[11px] text-white/95 font-medium truncate">
              {item.imageCaption || item.title}
            </span>
          </div>
        )}

        {/* Title & Category Pill */}
        <div className="mb-2">
          <span className="inline-block text-[11px] font-medium text-[#9E3B24] bg-[#9E3B24]/8 px-2 py-0.5 rounded-md mb-1.5">
            {item.category} · {item.audience}
          </span>
          <h3 className="font-serif-editorial text-xl sm:text-2xl font-bold text-[#1A1817] group-hover:text-[#9E3B24] transition-colors leading-snug">
            <a
              href={item.url}
              onClick={(e) => {
                e.preventDefault();
                onSelect(item);
              }}
              className="no-underline text-inherit"
            >
              {item.title}
            </a>
          </h3>
        </div>

        {/* Definition Excerpt */}
        <p className="text-sm text-[#4A443F] leading-relaxed line-clamp-3 mb-3">
          {item.definition}
        </p>

        {/* Example Callout Snippet */}
        {item.example && (
          <div className="rounded-xl bg-[#FAF6F0] border-l-2 border-[#C88A32] px-3 py-2 mb-3 text-xs text-[#4A443F] line-clamp-2 italic">
            <span className="font-semibold not-italic text-[#1A1817]">Пример: </span>
            {item.example}
          </div>
        )}
      </div>

      {/* Bottom Footer with Catalog Rod Punch-Hole & Permalink */}
      <div className="pt-3 mt-2 border-t border-[#E2D9CC]/80 flex items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1">
          {item.accessories.slice(0, 2).map((acc) => (
            <span
              key={acc}
              className="text-[11px] px-2 py-0.5 rounded-md bg-[#F3ECE2]/80 text-[#7A7167]"
            >
              {acc}
            </span>
          ))}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {/* Authentic library catalog punch-hole */}
          <span
            aria-hidden="true"
            title="Каталожная перфорация"
            className="w-3 h-3 rounded-full bg-[#FAF6F0] border border-[#C5B9A8] shadow-inner hidden sm:inline-block"
          />
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-[#9E3B24] group-hover:translate-x-0.5 transition-transform">
            <span>Открыть</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </span>
        </div>
      </div>
    </article>
  );
};
