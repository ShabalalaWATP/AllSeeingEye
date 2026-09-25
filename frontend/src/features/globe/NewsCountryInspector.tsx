import { useEffect, useRef } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { SourceLink } from '@/components/ui/SourceLink';
import type { NewsCountryContext } from './useNewsCountryContext';
import { newsSourceLabel, newsStories } from './newsFilters';

export function NewsCountryInspector({
  group,
  onClose,
  onSelect,
}: {
  group: NewsCountryContext;
  onClose: () => void;
  onSelect: (event: LiveEvent) => void;
}) {
  const close = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    close.current?.focus();
    const dismiss = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !event.defaultPrevented) {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', dismiss);
    return () => window.removeEventListener('keydown', dismiss);
  }, [onClose]);
  return (
    <aside
      aria-label="News country context details"
      className="map-details-inspector absolute bottom-16 right-16 z-20 max-h-[calc(100%-8rem)] w-80 max-w-[calc(100%-5rem)] overflow-y-auto rounded-lg border border-line bg-ground p-4 shadow-xl"
    >
      <header className="flex items-start justify-between gap-3">
        <div>
          <p className="text-2xs uppercase tracking-wider text-muted">News country context</p>
          <h2 className="mt-1 text-sm font-medium">{group.country.name}</h2>
        </div>
        <button
          ref={close}
          type="button"
          onClick={onClose}
          aria-label="Close news country context"
          className="min-h-9 px-2 text-muted"
        >
          ×
        </button>
      </header>
      <p className="mt-3 text-xs leading-5 text-muted">
        These reports carry source-supplied country context. The marker is a country reference, not
        an exact event location. Machine-coded geography and reporting claims remain unverified.
      </p>
      <ul className="mt-3 space-y-3">
        {newsStories(group.events)
          .slice(0, 25)
          .map(({ lead }) => (
            <li key={lead.id} className="rounded border border-line p-3 text-xs">
              <p className="mb-2 text-2xs text-muted">{newsSourceLabel(lead)}</p>
              <button
                className="w-full text-left leading-5 hover:text-cyan"
                type="button"
                onClick={() => onSelect(lead)}
              >
                {lead.title_en ?? lead.title}
              </button>
              <div className="mt-2">
                <SourceLink url={lead.url}>Read source</SourceLink>
              </div>
            </li>
          ))}
      </ul>
      <p className="mt-3 text-2xs text-muted">
        Up to 25 stories from the current bounded map sample. Related reports are not independent
        confirmation.
      </p>
    </aside>
  );
}
