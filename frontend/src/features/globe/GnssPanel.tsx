import { useId, useState } from 'react';
import type { JamCell } from '@/lib/api/aviation';
import { formatUtc } from '@/lib/format';
import type { useInterference } from './useInterference';
import { sameJamCell, type useGnssFilters } from './useGnssFilters';

const PAGE_SIZE = 20;

export function GnssPanel({
  enabled,
  data,
  filters,
  selected,
  onSelect,
  selectionDisabled,
}: {
  enabled: boolean;
  data: ReturnType<typeof useInterference>;
  filters: ReturnType<typeof useGnssFilters>;
  selected: JamCell | null;
  onSelect: (cell: JamCell) => void;
  selectionDisabled: boolean;
}) {
  const [page, setPage] = useState(0);
  const radioName = useId();
  const current = Math.min(page, Math.max(0, Math.ceil(filters.filtered.length / PAGE_SIZE) - 1));
  return (
    <section aria-label="GNSS observations" className="space-y-4 p-3 text-xs">
      <div>
        <h3 className="text-sm font-medium">Aircraft accuracy anomalies</h3>
        <p className="mt-1 leading-relaxed text-muted">
          Possible navigation interference, including GPS disruption. Aircraft accuracy alone cannot
          confirm jamming or spoofing.
        </p>
      </div>
      <div className="border-y border-line py-2 text-muted">
        <p>Worldwide · approximately 24 hours · updates every 5 minutes</p>
        <p className="mt-1">
          Snapshot received:{' '}
          {data.receivedAt === null
            ? 'Not available'
            : formatUtc(new Date(data.receivedAt).toISOString())}
        </p>
        <p className="mt-1">
          Latest aircraft observation:{' '}
          {data.updated_at ? formatUtc(data.updated_at) : 'Not available'}
        </p>
      </div>
      {!enabled ? (
        <p role="status">
          GPS interference is off. Use its switch above to load and show observations.
        </p>
      ) : (
        <>
          {data.error && (
            <p role="alert" className="text-critical">
              GNSS update failed: {data.error}{' '}
              {data.cells.length > 0 &&
                'The last successful snapshot is cached and may include older observations.'}
            </p>
          )}
          {data.loading && <p role="status">Updating GNSS observations…</p>}
          {data.limited && (
            <p role="status">
              The GNSS memory limit was reached. Some observations were omitted, so counts and
              shares represent a partial sample.
            </p>
          )}
          {filters.expired && (
            <p role="status">
              The snapshot is over 15 minutes old. Cached cells are hidden until an update succeeds.
            </p>
          )}
          {filters.stale && !filters.expired && (
            <p role="status">
              This cached snapshot is out of date. Refresh to check current observations.
            </p>
          )}
          <fieldset>
            <legend className="mb-2 font-medium">Accuracy flag</legend>
            <div className="flex gap-2">
              {(['all', 'red'] as const).map((value) => (
                <label
                  key={value}
                  className="flex min-h-9 flex-1 cursor-pointer items-center gap-2 rounded bg-white/5 px-2"
                >
                  <input
                    type="radio"
                    name={radioName}
                    checked={filters.level === value}
                    onChange={() => {
                      filters.setLevel(value);
                      setPage(0);
                    }}
                    className="accent-cyan"
                  />
                  {value === 'all' ? 'All flagged' : 'Red only'}
                </label>
              ))}
            </div>
          </fieldset>
          <label className="flex items-center justify-between gap-3">
            Minimum observations
            <select
              className="min-h-9 rounded border border-line bg-surface px-2"
              value={filters.minimum}
              onChange={(event) => {
                filters.setMinimum(Number(event.target.value));
                setPage(0);
              }}
            >
              {[5, 10, 25, 50].map((count) => (
                <option key={count} value={count}>
                  {count}+
                </option>
              ))}
            </select>
          </label>
          <p className="text-muted">
            Amber: 2–10% adjusted low-accuracy share. Red: over 10%. These percentages are not a
            probability of jamming.
          </p>
          <div className="flex items-center justify-between border-t border-line pt-2">
            <h3 className="font-medium">
              {filters.filtered.length.toLocaleString('en-GB')} flagged{' '}
              {filters.filtered.length === 1 ? 'cell' : 'cells'}
            </h3>
            <button
              type="button"
              disabled={data.loading}
              className="min-h-9 text-cyan disabled:opacity-50"
              onClick={data.refresh}
            >
              Refresh GNSS
            </button>
          </div>
          {selectionDisabled && (
            <p className="text-muted">Finish drawing or measuring to locate a cell.</p>
          )}
          {!data.loading && !data.error && filters.filtered.length === 0 && (
            <p role="status">
              No flagged cells match these filters. Coverage gaps do not establish an absence of
              interference.
            </p>
          )}
          <ul className="divide-y divide-line">
            {filters.filtered.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE).map((cell) => (
              <li key={`${cell.lon}:${cell.lat}:${cell.size}`}>
                <button
                  type="button"
                  aria-label={`Locate GNSS cell ${cell.lat}, ${cell.lon}`}
                  aria-pressed={sameJamCell(selected, cell)}
                  disabled={selectionDisabled}
                  onClick={() => onSelect(cell)}
                  className="flex min-h-12 w-full items-center justify-between gap-2 rounded px-2 text-left hover:bg-white/5 aria-pressed:bg-cyan/10 disabled:opacity-50"
                >
                  <span>
                    <span className={cell.level === 'red' ? 'text-red-400' : 'text-amber-300'}>
                      {cell.level === 'red' ? 'Red' : 'Amber'} · {cell.percent_bad.toFixed(1)}%
                    </span>
                    <span className="mt-1 block font-mono text-muted">
                      {cell.lat.toFixed(1)}°, {cell.lon.toFixed(1)}°
                    </span>
                  </span>
                  <span className="text-right text-muted">
                    {(cell.good + cell.bad).toLocaleString('en-GB')} obs.
                    <span className="block text-cyan">Locate ›</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {filters.filtered.length > PAGE_SIZE && (
            <nav aria-label="GNSS cell pages" className="flex items-center justify-between">
              <button
                className="min-h-9 disabled:opacity-40"
                disabled={current === 0}
                onClick={() => setPage(current - 1)}
              >
                Previous
              </button>
              <span>
                {current + 1} / {Math.ceil(filters.filtered.length / PAGE_SIZE)}
              </span>
              <button
                className="min-h-9 disabled:opacity-40"
                disabled={(current + 1) * PAGE_SIZE >= filters.filtered.length}
                onClick={() => setPage(current + 1)}
              >
                Next
              </button>
            </nav>
          )}
        </>
      )}
      <details className="border-t border-line pt-1 text-muted">
        <summary className="cursor-pointer py-2 font-medium text-text">
          Source and interpretation
        </summary>
        <p>
          Aircraft-reported ADS-B accuracy (NACp), aggregated by ASE in 1° cells. Counts are
          aircraft-cell-hour observations, not unique aircraft. Low or unavailable accuracy (NACp
          0–5) takes precedence within each cell/hour. The adjusted share subtracts one low-accuracy
          observation.
        </p>
        <p className="mt-2">
          Hourly buckets retain approximately 24 hours, up to 25 hours at the oldest boundary.
          Source coverage varies by receiver network.
        </p>
        <p className="mt-2">
          This layer has its own observation window and is independent of the flight switch and
          general event filters. Cells are not interference boundaries or transmitter locations. It
          does not identify a GNSS constellation or confirm spoofing.
        </p>
        <a
          className="mt-3 inline-block min-h-9 text-cyan underline"
          href="https://www.easa.europa.eu/en/domains/air-operations/global-navigation-satellite-system-outages-and-alterations"
          target="_blank"
          rel="noreferrer"
        >
          EASA guidance and reported affected areas ↗
        </a>
      </details>
    </section>
  );
}
