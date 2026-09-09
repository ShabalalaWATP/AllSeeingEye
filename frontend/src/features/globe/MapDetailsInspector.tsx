import { useEffect, useRef, useState } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { JamCell } from '@/lib/api/aviation';
import type { Cluster } from './layers/clusters';
import { formatUtc } from '@/lib/format';
export type MapDetails = { kind: 'cluster'; cluster: Cluster } | { kind: 'jam'; cell: JamCell };
export function MapDetailsInspector({
  details,
  cells,
  events,
  updatedAt,
  onSelect,
  onClose,
}: {
  details: MapDetails;
  cells: readonly JamCell[];
  events: readonly LiveEvent[];
  updatedAt: string | null;
  onSelect: (event: LiveEvent) => void;
  onClose: () => void;
}) {
  const close = useRef<HTMLButtonElement>(null);
  const [page, setPage] = useState(0);
  useEffect(() => {
    const opener = document.activeElement;
    close.current?.focus();
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !event.defaultPrevented) {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', escape);
    return () => {
      window.removeEventListener('keydown', escape);
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, [onClose]);
  const ids = new Set(
    details.kind === 'cluster' ? details.cluster.members?.map((item) => item.id) : [],
  );
  const members = events.filter((event) => ids.has(event.id));
  const current = Math.min(page, Math.max(0, Math.ceil(members.length / 20) - 1));
  const cell =
    details.kind === 'jam'
      ? cells.find(
          (item) =>
            item.lon === details.cell.lon &&
            item.lat === details.cell.lat &&
            item.size === details.cell.size &&
            item.level !== 'green',
        )
      : null;
  return (
    <aside
      aria-label="Map details"
      className="absolute top-32 right-3 bottom-24 z-10 flex w-[calc(100%-1.5rem)] flex-col rounded-md border border-line bg-surface/95 p-4 backdrop-blur sm:w-80 lg:top-16"
    >
      <header className="flex items-start justify-between gap-2">
        <h2 className="font-medium">
          {details.kind === 'jam' ? 'GNSS accuracy cell' : 'Items in this cluster'}
        </h2>
        <button
          ref={close}
          type="button"
          onClick={onClose}
          className="px-2 py-1 text-sm"
          aria-label="Close map details"
        >
          Close
        </button>
      </header>
      <div className="mt-4 space-y-3 overflow-y-auto text-sm">
        {details.kind === 'jam' ? (
          !cell ? (
            <p role="status">
              This GNSS cell is no longer visible with the current filters or observations.
            </p>
          ) : (
            <>
              <p>Poor position accuracy reports, not confirmation of intentional interference.</p>
              <dl className="space-y-2 text-xs">
                <dt>Cell centre / angular width</dt>
                <dd>
                  {cell.lat}, {cell.lon} / {cell.size} degrees
                </dd>
                <dt>Accuracy observations</dt>
                <dd>
                  {cell.bad} poor; {cell.good} good
                </dd>
                <dt>Adjusted poor-accuracy share</dt>
                <dd>{cell.percent_bad}%</dd>
                <dt>Flag</dt>
                <dd>{cell.level}</dd>
                <dt>Latest observation across all GNSS cells</dt>
                <dd>{updatedAt ? formatUtc(updatedAt) : 'Not recorded'}</dd>
              </dl>
              <p className="text-xs text-muted">
                Counts are aircraft-per-cell-per-hour observations over approximately 24 hours, not
                unique aircraft. The adjusted share subtracts one poor observation before dividing
                by all observations. The square is an aggregation cell, not a measured interference
                boundary or an emitter location.
              </p>
            </>
          )
        ) : (
          <>
            <p>
              {members.length} currently visible items. Screen picking is bounded to 64 hits; zoom
              or filter crowded areas to inspect further items. Choose an item to inspect its source
              and details. Items may share a location.
            </p>
            <ul>
              {members.slice(current * 20, (current + 1) * 20).map((event) => (
                <li key={event.id}>
                  <button
                    type="button"
                    className="w-full border-b border-line py-3 text-left text-sm hover:text-cyan"
                    onClick={() => onSelect(event)}
                  >
                    {event.title}
                  </button>
                </li>
              ))}
            </ul>
            {members.length > 20 && (
              <div className="flex justify-between">
                <button disabled={current === 0} onClick={() => setPage(current - 1)}>
                  Previous items
                </button>
                <button
                  disabled={(current + 1) * 20 >= members.length}
                  onClick={() => setPage(current + 1)}
                >
                  Next items
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </aside>
  );
}
