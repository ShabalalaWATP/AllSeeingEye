import { BASIS_LABELS, type PublicFigure } from '@/lib/api/figures';
import { formatUtc } from '@/lib/format';

import { MapControlIcon } from '../MapControlIcon';
import { FigurePortrait } from './FigurePortrait';
import type { FigureState } from './useFigures';

export function FigurePanel({
  figures,
  onSelect,
}: {
  figures: FigureState;
  onSelect?: (figure: PublicFigure) => void;
}) {
  const reported = figures.visible.filter((figure) => figure.placement.basis !== 'seat').length;
  return (
    <section aria-label="Public figures" className="space-y-4 p-1 text-xs">
      <button
        type="button"
        role="switch"
        aria-label="Show public figures"
        aria-checked={figures.enabled}
        onClick={() => figures.setEnabled(!figures.enabled)}
        className="flex min-h-16 w-full items-center gap-3 rounded-lg border border-line px-3 py-3 text-left hover:bg-white/5 focus-visible:outline-2 focus-visible:outline-cyan"
      >
        <span className="text-cyan">
          <MapControlIcon name="figure" />
        </span>
        <span className="flex-1 text-sm font-medium">Show public figures</span>
        <span
          aria-hidden="true"
          className={`flex h-5 w-9 shrink-0 items-center rounded-full p-0.5 ${figures.enabled ? 'bg-cyan/70' : 'bg-white/15'}`}
        >
          <span
            className={`h-4 w-4 rounded-full bg-white transition-transform ${figures.enabled ? 'translate-x-4' : ''}`}
          />
        </span>
      </button>
      <p className="text-muted">
        Heads of state and government, named senior ministers and chiefs for the UK, US, Russia,
        China and Belarus, and the leaders of NATO, the UN and the EU, placed where public reporting
        names them in the last three days. With no located report the marker sits at the seat of
        office. Nothing here is a confirmed position or a movement record.
      </p>
      {figures.enabled && (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              disabled={figures.loading}
              onClick={figures.refresh}
              className="min-h-11 underline"
            >
              Refresh
            </button>
            <label className="flex min-h-11 items-center gap-2">
              <input
                type="checkbox"
                checked={figures.reportedOnly}
                onChange={(event) => figures.setReportedOnly(event.target.checked)}
              />
              Only reported placements
            </label>
          </div>
          {figures.loading && <p role="status">Loading public figures…</p>}
          {figures.error && <p role="alert">{figures.error}</p>}
          {figures.board && (
            <p className="text-muted">
              {figures.visible.length} shown, {reported} placed by reporting, from{' '}
              {figures.board.events_scanned} reports in {figures.board.window_hours} h. Roster
              retrieved {formatUtc(figures.board.roster_retrieved_at)}.
            </p>
          )}
          <label className="block">
            Find a figure
            <input
              type="search"
              placeholder="Name, office or country"
              value={figures.query}
              onChange={(event) => figures.setQuery(event.target.value)}
              maxLength={120}
              className="mt-2 min-h-11 w-full rounded border border-line bg-surface p-2"
            />
          </label>
          <ul aria-label="Figures on the map" className="max-h-80 space-y-1 overflow-y-auto">
            {figures.visible.map((figure) => (
              <li key={figure.id}>
                <button
                  type="button"
                  onClick={() => onSelect?.(figure)}
                  aria-current={figures.selected?.id === figure.id ? 'true' : undefined}
                  className="flex min-h-11 w-full items-center gap-3 rounded px-2 py-1 text-left hover:bg-white/5 aria-[current=true]:bg-white/10"
                >
                  <FigurePortrait figure={figure} size="sm" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium text-text">{figure.name}</span>
                    <span className="block truncate text-muted">{figure.office}</span>
                  </span>
                  <span className="shrink-0 font-mono text-[10px] uppercase text-muted">
                    {BASIS_LABELS[figure.placement.basis]}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
