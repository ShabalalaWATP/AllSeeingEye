import { useId } from 'react';
import { LiveCoverage } from './LiveCoverage';
import type { Category, StoreStats } from '@/lib/api/eventSchemas';
import type { StreamStatus } from '@/lib/sse';

import { ConnectionStatus } from './ConnectionStatus';
import { CATEGORY_STYLES } from '@/lib/categories';

const OTHER_TOPICS = ['cyber', 'social', 'political', 'humanitarian', 'economic'] as const;

export interface LayerPanelProps {
  counts: Partial<Record<Category, number>>;
  hidden: readonly Category[];
  stats: StoreStats | null;
  status: StreamStatus;
  error: string | null;
  windowHours: number | null;
  onWindow: (hours: number | null) => void;
  onToggle: (category: Category) => void;
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

/** Shared event filters and additional topics; each main layer keeps its own controls. */
export function LayerPanel({
  counts,
  hidden,
  stats,
  status,
  error,
  windowHours,
  onWindow,
  onToggle,
}: LayerPanelProps) {
  const windowName = useId();
  return (
    <section
      aria-label="Topics and time controls"
      className="shrink-0 rounded-md border border-line bg-surface/90 p-2 backdrop-blur"
    >
      <div className="mb-1 flex items-center justify-between px-1">
        <h3 className="text-sm font-medium">Topics &amp; time</h3>
        <ConnectionStatus status={status} />
      </div>
      <p className="mb-2 px-1 text-xs text-muted">
        Use the left rail to switch each main layer on or off. Its Filters button opens options for
        that layer. Map appearance is under Map style on the right.
      </p>
      <div className="flex items-center justify-between px-1">
        <h3 className="py-2 text-xs font-medium">Additional topics</h3>
        <button
          type="button"
          className="min-h-9 text-xs text-cyan disabled:opacity-40"
          disabled={!OTHER_TOPICS.some((topic) => hidden.includes(topic))}
          onClick={() =>
            OTHER_TOPICS.filter((topic) => hidden.includes(topic)).forEach((topic) =>
              onToggle(topic),
            )
          }
        >
          Show all topics
        </button>
      </div>
      <ul className="space-y-0.5" aria-label="Additional event topics">
        {OTHER_TOPICS.map((category) => {
          const style = CATEGORY_STYLES[category];
          const shown = !hidden.includes(category);
          return (
            <li key={category}>
              <button
                type="button"
                role="switch"
                aria-checked={shown}
                onClick={() => {
                  onToggle(category);
                }}
                className={`flex min-h-11 w-full items-center gap-2 rounded px-1.5 py-1 text-left text-sm transition-colors hover:bg-surface-2 lg:min-h-0 ${
                  shown ? 'text-text' : 'text-muted'
                }`}
              >
                <span
                  aria-hidden="true"
                  className="inline-block h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: style.css, opacity: shown ? 1 : 0.3 }}
                />
                <span className="flex-1">{style.label}</span>
                <span aria-hidden="true" className="text-[10px] text-muted">
                  {shown ? 'On' : 'Off'}
                </span>{' '}
                <span className="font-mono text-xs text-muted tabular-nums">
                  {counts[category] ?? 0}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      <div className="mt-3 flex items-center justify-between px-1">
        <h3 className="text-xs font-medium">Event time window</h3>
        <button
          type="button"
          disabled={windowHours === null}
          onClick={() => onWindow(null)}
          className="min-h-9 text-xs text-cyan disabled:opacity-40"
        >
          Clear time filter
        </button>
      </div>
      <p className="px-1 text-xs text-muted">
        Applies to live events across categories. Layer and topic switches narrow this further.
        GNSS, CCTV and infrastructure use their own coverage.
      </p>
      <div
        role="radiogroup"
        aria-label="Time window"
        className="mt-1 flex flex-wrap gap-1 border-t border-line px-1 pt-1.5"
      >
        {WINDOWS.map((option) => (
          <label key={option.label} className="cursor-pointer">
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
            <span className="inline-flex min-h-11 items-center rounded px-2 py-0.5 font-mono text-[11px] text-muted hover:text-text peer-checked:bg-surface-2 peer-checked:text-text peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-ember lg:min-h-0 lg:px-1.5">
              {option.label}
            </span>
          </label>
        ))}
      </div>
      <details className="mt-3 border-t border-line px-1 pt-1 text-xs">
        <summary className="min-h-9 cursor-pointer py-2 font-medium">
          Connection and coverage
        </summary>
        {stats !== null && (
          <p className="mt-1 font-mono text-[11px] text-muted">
            Retained on server: <span>{formatBudget(stats)}</span>
          </p>
        )}
        <LiveCoverage
          filteredCount={Object.values(counts).reduce((total, count) => total + count, 0)}
        />
      </details>
      {error !== null && (
        <p role="alert" className="mt-1 px-1 text-xs text-critical">
          {error}
        </p>
      )}
    </section>
  );
}
