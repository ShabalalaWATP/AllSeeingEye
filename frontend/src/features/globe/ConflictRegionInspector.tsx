import { useEffect, useRef } from 'react';
import { Link } from 'react-router';
import { regionLabel, type ConflictRegion } from './conflictRegions';

export function ConflictRegionInspector({
  region,
  onClose,
}: {
  region: ConflictRegion;
  onClose: () => void;
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
  const { card } = region;
  return (
    <aside
      aria-label="Conflict region details"
      className="map-details-inspector absolute bottom-16 right-16 z-20 max-h-[calc(100%-8rem)] w-80 max-w-[calc(100%-5rem)] overflow-y-auto rounded-lg border border-line bg-ground p-4 shadow-xl"
    >
      <header className="flex items-start justify-between gap-3">
        <div>
          <p className="text-2xs uppercase tracking-wider text-cyan">{regionLabel(region)}</p>
          <h2 className="mt-1 text-sm font-medium">{card.conflict.name}</h2>
        </div>
        <button
          ref={close}
          type="button"
          onClick={onClose}
          aria-label="Close conflict region details"
          className="min-h-9 px-2 text-muted hover:text-cyan"
        >
          ×
        </button>
      </header>
      <p className="mt-3 text-xs text-muted">{card.conflict.summary}</p>
      <p className="mt-2 text-[11px] text-muted">
        Curated catalogue context, not a live status assessment. The outline is a broad research
        area, not a frontline or an incident location.
      </p>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
        <div>
          <dt className="text-muted">Violence groups / 7 d</dt>
          <dd className="mt-1 font-mono text-lg">{card.activity.last_7d}</dd>
        </div>
        <div>
          <dt className="text-muted">Related items / 7 d</dt>
          <dd className="mt-1 font-mono text-lg">{card.reporting_7d}</dd>
        </div>
      </dl>
      <p className="mt-2 text-2xs text-muted">
        Source reports grouped by shared evidence, not independent verification. Zero retained
        reports does not establish an absence of conflict.
      </p>
      {card.latest && (
        <div className="mt-4 border-t border-line pt-3">
          <p className="text-2xs text-muted">
            Latest retained violence report · {card.latest.source_id.replaceAll('_', ' ')}
          </p>
          <p className="mt-1 text-xs">{card.latest.title}</p>
        </div>
      )}
      <Link
        to={`/trackers/conflicts/${encodeURIComponent(card.conflict.id)}`}
        className="mt-4 inline-flex min-h-10 items-center text-xs text-cyan underline"
      >
        Open evidence, sources and timeline
      </Link>
    </aside>
  );
}
