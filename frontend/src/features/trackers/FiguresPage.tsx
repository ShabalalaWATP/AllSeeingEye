import { useMemo, useState } from 'react';

import { describeError } from '@/lib/api/errors';
import {
  BASIS_LABELS,
  ROLE_LABELS,
  fetchFigures,
  portraitUrl,
  type FigureBoard,
  type PublicFigure,
} from '@/lib/api/figures';
import { formatUtc } from '@/lib/format';
import { useResource } from '@/lib/hooks/useResource';

import { EventList, ModulePage, Stat } from './ModuleParts';

const RING: Record<PublicFigure['placement']['basis'], string> = {
  reported_place: 'ring-cyan',
  reported_country: 'ring-amber-300',
  seat: 'ring-muted/50',
};

function FigureCard({
  figure,
  open,
  onToggle,
}: {
  figure: PublicFigure;
  open: boolean;
  onToggle: () => void;
}) {
  const url = portraitUrl(figure);
  return (
    <li className="rounded-card border border-line bg-surface p-3">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="flex w-full items-center gap-3 text-left"
      >
        {url ? (
          <img
            src={url}
            alt=""
            width={64}
            height={64}
            className={`size-12 shrink-0 rounded-full bg-surface-2 ring-2 ${RING[figure.placement.basis]}`}
          />
        ) : (
          <span
            aria-hidden="true"
            className={`flex size-12 shrink-0 items-center justify-center rounded-full bg-surface-2 ring-2 ${RING[figure.placement.basis]}`}
          >
            {figure.name.slice(0, 1)}
          </span>
        )}
        <span className="min-w-0 flex-1">
          <span className="block truncate font-medium text-text">{figure.name}</span>
          <span className="block truncate text-xs text-muted">{figure.office}</span>
          <span className="mt-1 block font-mono text-[11px] uppercase text-muted">
            {BASIS_LABELS[figure.placement.basis]} · {figure.mentions}{' '}
            {figure.mentions === 1 ? 'mention' : 'mentions'}
          </span>
        </span>
      </button>
      {open && (
        <div className="mt-3 flex flex-col gap-3 text-xs">
          <p className="text-muted">
            {ROLE_LABELS[figure.role]}
            {figure.country_iso ? ` · ${figure.country_iso}` : ''} · seat {figure.seat_name}
          </p>
          <p className="leading-relaxed text-muted">{figure.placement.detail}</p>
          <EventList label={`Reporting naming ${figure.name}`} events={figure.latest} />
          {figure.portrait && (
            <p className="text-[11px] text-muted">
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
        </div>
      )}
    </li>
  );
}

/** The board itself; the page wraps it with loading, errors and the shared frame. */
export function FiguresBoard({ board }: { board: FigureBoard }) {
  const [open, setOpen] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const term = query.trim().toLocaleLowerCase('en-GB');
  const visible = useMemo(
    () =>
      [...board.figures]
        .filter((figure) =>
          term
            ? `${figure.name} ${figure.office} ${figure.country_iso ?? ''} ${figure.organisation ?? ''}`
                .toLocaleLowerCase('en-GB')
                .includes(term)
            : true,
        )
        .sort((a, b) => b.mentions - a.mentions || a.name.localeCompare(b.name, 'en-GB')),
    [board.figures, term],
  );
  const reported = board.figures.filter((figure) => figure.placement.basis !== 'seat').length;
  return (
    <>
      <div className="grid gap-2 sm:grid-cols-3">
        <Stat label="Office-holders tracked" value={board.figures.length} />
        <Stat label="Placed by reporting" value={reported} />
        <Stat label={`Reports scanned, ${board.window_hours} h`} value={board.events_scanned} />
      </div>
      <p className="text-sm text-muted">{board.caveat}</p>
      <p className="font-mono text-xs text-muted">
        Roster retrieved {formatUtc(board.roster_retrieved_at)} · {board.source_note}
      </p>
      <label className="block max-w-sm text-sm">
        Find a figure
        <input
          type="search"
          placeholder="Name, office or country"
          value={query}
          onChange={(event) => setQuery(event.target.value.slice(0, 120))}
          maxLength={120}
          className="mt-1 min-h-11 w-full rounded border border-line bg-surface px-2"
        />
      </label>
      <ul aria-label="Public figures" className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {visible.map((figure) => (
          <FigureCard
            key={figure.id}
            figure={figure}
            open={open === figure.id}
            onToggle={() => setOpen(open === figure.id ? null : figure.id)}
          />
        ))}
      </ul>
    </>
  );
}

export default function FiguresPage() {
  const { data, error, loading } = useResource(() => fetchFigures());
  return (
    <ModulePage
      title="Public figures"
      blurb="Current heads of state and government and the leaders of NATO, the UN and the EU, with where public reporting names them in the last three days. Office-holders only, from public schedules and reporting; no private individuals, staff or families."
      template={null}
      loading={loading}
      error={error === null ? null : describeError(error)}
    >
      {data !== null && <FiguresBoard board={data} />}
    </ModulePage>
  );
}
