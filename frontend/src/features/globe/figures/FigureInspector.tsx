import { useEffect, useRef } from 'react';

import { BASIS_LABELS, ROLE_LABELS, type PublicFigure } from '@/lib/api/figures';
import { formatUtc } from '@/lib/format';

import { FigurePortrait } from './FigurePortrait';
import { FigureLocationPicker } from './FigureLocationPicker';

export function FigureInspector({
  figure,
  onClose,
  visibleFigures = [],
  onSelectFigure,
}: {
  figure: PublicFigure;
  onClose: () => void;
  visibleFigures?: readonly PublicFigure[];
  onSelectFigure?: (figure: PublicFigure) => void;
}) {
  const close = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const opener = document.activeElement;
    close.current?.focus();
    const dismiss = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !event.defaultPrevented) {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', dismiss);
    return () => {
      window.removeEventListener('keydown', dismiss);
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, [onClose]);
  const { placement } = figure;
  return (
    <aside
      aria-label="Public figure details"
      className="map-details-inspector absolute bottom-16 right-16 z-20 max-h-[calc(100%-6rem)] w-80 max-w-[calc(100%-5rem)] overflow-y-auto rounded-lg border border-line bg-ground p-4 shadow-xl"
    >
      <header className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <FigurePortrait figure={figure} size="lg" />
          <div>
            <p className="text-2xs uppercase tracking-wider text-cyan">
              {ROLE_LABELS[figure.role]}
              {figure.country_iso ? ` · ${figure.country_iso}` : ''}
            </p>
            <h2 className="mt-1 text-sm font-medium">{figure.name}</h2>
            <p className="text-xs text-muted">{figure.office}</p>
          </div>
        </div>
        <button
          ref={close}
          type="button"
          onClick={onClose}
          aria-label="Close public figure details"
          className="px-2 py-1 text-muted hover:text-cyan"
        >
          ×
        </button>
      </header>
      {onSelectFigure && (
        <FigureLocationPicker
          figure={figure}
          visibleFigures={visibleFigures}
          onSelect={onSelectFigure}
        />
      )}
      <p className="mt-3 text-xs font-medium text-cyan">{BASIS_LABELS[placement.basis]}</p>
      <p className="mt-1 text-xs leading-relaxed text-muted">{placement.detail}</p>
      {placement.published_at && (
        <p className="mt-1 font-mono text-[11px] text-muted">
          Report published {formatUtc(placement.published_at)}
        </p>
      )}
      <section aria-label="Recent reporting" className="mt-3">
        <h3 className="text-xs font-medium">
          Recent reporting ({figure.mentions} {figure.mentions === 1 ? 'mention' : 'mentions'})
        </h3>
        {figure.latest.length === 0 ? (
          <p className="mt-1 text-xs text-muted">
            No retained report names {figure.name} in this window. That is an absence of collected
            reporting, not evidence of location.
          </p>
        ) : (
          <ul className="mt-1 space-y-1 text-xs">
            {figure.latest.map((event) => (
              <li key={event.id} className="leading-snug">
                {event.url ? (
                  <a href={event.url} target="_blank" rel="noreferrer" className="underline">
                    {event.title_en ?? event.title}
                  </a>
                ) : (
                  <span>{event.title_en ?? event.title}</span>
                )}
                <span className="ml-1 font-mono text-2xs text-muted">
                  {event.grade}
                  {event.published_at ? ` · ${formatUtc(event.published_at)}` : ''}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
      {figure.portrait && (
        <p className="mt-3 text-[11px] leading-relaxed text-muted">
          Portrait: {figure.portrait.credit}, {figure.portrait.licence}, via{' '}
          <a
            href={figure.portrait.source_url}
            target="_blank"
            rel="noreferrer"
            className="underline"
          >
            Wikimedia Commons
          </a>
          .
        </p>
      )}
    </aside>
  );
}
