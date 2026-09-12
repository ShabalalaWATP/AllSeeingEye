import { useId } from 'react';
import { MapToolIntro } from '@/components/maps/MapToolIntro';
import { LiveCoverage } from './LiveCoverage';
import type { Category, StoreStats } from '@/lib/api/eventSchemas';
import type { StreamStatus } from '@/lib/sse';

import { ConnectionStatus } from './ConnectionStatus';
export interface LayerPanelProps {
  counts: Partial<Record<Category, number>>;
  stats: StoreStats | null;
  status: StreamStatus;
  error: string | null;
  windowHours: number | null;
  onWindow: (hours: number | null) => void;
}

const MEBIBYTE = 1_048_576;

/** The time windows offered, in hours; null is the whole retained window. */
export const WINDOWS: readonly { hours: number | null; label: string }[] = [
  { hours: 1, label: '1 h' },
  { hours: 6, label: '6 h' },
  { hours: 24, label: '24 h' },
  { hours: 72, label: '72 h' },
  { hours: 168, label: '7 d' },
  { hours: null, label: 'All' },
];

export function formatBudget(stats: StoreStats): string {
  const used = (stats.estimated_bytes / MEBIBYTE).toFixed(1);
  const budget = Math.round(stats.budget_bytes / MEBIBYTE);
  return `${stats.total} events, ${used} of ${budget} MB`;
}

/** Shared time controls; layer selection belongs to the left rail. */
export function LayerPanel({
  counts,
  stats,
  status,
  error,
  windowHours,
  onWindow,
}: LayerPanelProps) {
  const windowName = useId();
  return (
    <section aria-label="Event time controls" className="map-tool-workspace">
      <MapToolIntro
        title="Event time"
        description="Choose how recent the records on your map should be. Counts describe collected records, not complete coverage."
      />
      <ConnectionStatus status={status} />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="map-tool-section-title">Event time window</h3>
        <button
          type="button"
          disabled={windowHours === null}
          onClick={() => onWindow(null)}
          className="map-tool-text-button"
        >
          Clear time filter
        </button>
      </div>
      <p className="map-tool-help">
        Applies to live events across categories and the News briefing. Each layer has its own
        selection controls. GNSS, CCTV and infrastructure use their own coverage.
      </p>
      <div role="radiogroup" aria-label="Time window" className="grid grid-cols-3 gap-2">
        {WINDOWS.map((option) => (
          <label key={option.label} className="map-tool-radio-option">
            <input
              type="radio"
              name={windowName}
              value={option.label}
              checked={option.hours === windowHours}
              onChange={() => {
                onWindow(option.hours);
              }}
              className="peer sr-only"
            />
            <span className="font-mono">{option.label}</span>
          </label>
        ))}
      </div>
      <details className="map-tool-disclosure">
        <summary className="min-h-9 cursor-pointer py-2 font-medium">
          Connection and coverage
        </summary>
        {stats !== null && (
          <p className="mt-1 font-mono text-[11px] text-muted">
            Retained on server: <span>{formatBudget(stats)}</span>
          </p>
        )}
        <p className="map-tool-help mb-3">
          Use the left rail for each main layer. Regional conflict markers follow the nation
          selection only. Context bulletins show their own scope and dates. Map appearance is under
          Map style on the right.
        </p>
        <LiveCoverage
          filteredCount={Object.values(counts).reduce((total, count) => total + count, 0)}
        />
      </details>
      {error !== null && (
        <p role="alert" className="map-tool-notice">
          {error}
        </p>
      )}
    </section>
  );
}
