import { Alert, LoadingNote } from '@/components/ui/Alert';
import { describeError } from '@/lib/api/errors';
import {
  fetchUkraineBoard,
  fetchUkraineControl,
  type UkraineBoard,
  type UkraineControl,
} from '@/lib/api/ukraine';
import { formatAgo } from '@/lib/format';

import { FiguresStrip } from './FiguresStrip';
import { SourcesFooter } from './SourcesFooter';
import { UkraineMap } from './UkraineMap';
import { UpdatesTabs } from './UpdatesTabs';
import { useUkraineBoard } from './useUkraineBoard';

const SECTIONS = [
  ['map', 'Map'],
  ['updates', 'Updates'],
  ['figures', 'Figures'],
  ['sources', 'Sources'],
] as const;

function Freshness({ board, now }: { board: UkraineBoard; now: number }) {
  const { freshness } = board;
  const chips = [
    ['Control snapshot', freshness.control_assessed],
    ['ISW assessment', freshness.assessment_published],
    ['General Staff claim', freshness.claim_reported],
    ['Latest item', freshness.latest_update],
  ] as const;
  return (
    <ul aria-label="Freshness" className="flex flex-wrap gap-2">
      {chips.map(([label, value]) => (
        <li
          key={label}
          className="rounded border border-line bg-surface px-2 py-1 font-mono text-[11px] text-muted"
        >
          {label}: {value ? formatAgo(value, now) : 'not yet collected'}
        </li>
      ))}
    </ul>
  );
}

/** Loaders are injectable so the DEV preview can frame the page with fixture data. */
export default function UkrainePage({
  loadBoard = fetchUkraineBoard,
  loadControl = fetchUkraineControl,
}: {
  loadBoard?: () => Promise<UkraineBoard>;
  loadControl?: () => Promise<UkraineControl>;
}) {
  const { data: loaded, error, loading } = useUkraineBoard(loadBoard);
  const data = loaded?.board ?? null;
  const now = loaded?.loadedAt ?? 0;
  return (
    <article className="flex h-full flex-col gap-6 overflow-y-auto p-6">
      <header className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-semibold">Ukraine war</h1>
          {data ? (
            <span
              className="rounded bg-surface-2 px-2 py-0.5 font-mono text-xs text-text"
              title={
                data.day_basis === 'claimed'
                  ? "Day count as stated in the General Staff of Ukraine's latest summary."
                  : 'Day count from 24 February 2022; no General Staff summary collected yet.'
              }
            >
              Day {data.day_number.toLocaleString('en-GB')} of the full-scale invasion
            </span>
          ) : null}
        </div>
        <p className="max-w-3xl text-sm text-muted">
          Reported control, the belligerents&apos; own figures, published assessments and retained
          reporting on Russia&apos;s war in Ukraine. Every element names who reported it and on what
          basis. Nothing here is verified by this application.
        </p>
        {data ? <Freshness board={data} now={now} /> : null}
        <nav aria-label="Page sections" className="flex flex-wrap gap-1">
          {SECTIONS.map(([id, label]) => (
            <a
              key={id}
              href={`#${id}`}
              className="min-h-9 rounded border border-line px-3 py-1.5 text-xs text-muted hover:text-text"
            >
              {label}
            </a>
          ))}
        </nav>
      </header>
      {error ? <Alert tone="error">{describeError(error)}</Alert> : null}
      {loading && !data ? <LoadingNote label="Loading the Ukraine board" /> : null}
      <UkraineMap load={loadControl} />
      {data ? <UpdatesTabs updates={data.updates} /> : null}
      {data ? <FiguresStrip board={data} /> : null}
      <SourcesFooter control={data?.control ?? null} />
    </article>
  );
}
