import { useId } from 'react';
import { LiveCoverage } from './LiveCoverage';

import type { Category, StoreStats } from '@/lib/api/eventSchemas';
import type { StreamStatus } from '@/lib/sse';

import { ConnectionStatus } from './ConnectionStatus';
import { CATEGORY_STYLES, ORDERED_CATEGORIES } from '@/lib/categories';

export interface LayerPanelProps {
  counts: Partial<Record<Category, number>>;
  hidden: readonly Category[];
  stats: StoreStats | null;
  status: StreamStatus;
  error: string | null;
  terminator: boolean;
  lite: boolean;
  windowHours: number | null;
  onWindow: (hours: number | null) => void;
  onToggle: (category: Category) => void;
  onToggleTerminator: () => void;
  onToggleLite: () => void;
  interference: boolean;
  onToggleInterference: () => void;
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

/** Per-category visibility switches with live counts, plus the store budget line. */
function Toggle({
  label,
  checked,
  onToggle,
}: {
  label: string;
  checked: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={onToggle}
      className={`flex min-h-11 w-full items-center justify-between rounded px-1.5 py-1 text-left text-sm hover:bg-surface-2 lg:min-h-0 ${
        checked ? 'text-text' : 'text-muted'
      }`}
    >
      <span>{label}</span>{' '}
      <span className="font-mono text-[11px] uppercase text-muted">{checked ? 'on' : 'off'}</span>
    </button>
  );
}

export function LayerPanel({
  counts,
  hidden,
  stats,
  status,
  error,
  terminator,
  lite,
  windowHours,
  onWindow,
  onToggle,
  onToggleTerminator,
  onToggleLite,
  interference,
  onToggleInterference,
}: LayerPanelProps) {
  const windowName = useId();
  return (
    <section
      aria-label="Layers"
      className="shrink-0 rounded-md border border-line bg-surface/90 p-2 backdrop-blur"
    >
      <div className="mb-1 flex items-center justify-between px-1">
        <h2 className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted">Layers</h2>
        <ConnectionStatus status={status} />
      </div>
      <ul className="space-y-0.5">
        {ORDERED_CATEGORIES.map((category) => {
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
                <span className="flex-1">{style.label}</span>{' '}
                <span className="font-mono text-xs text-muted tabular-nums">
                  {counts[category] ?? 0}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
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
      <div className="mt-1 border-t border-line pt-1">
        <Toggle label="Day and night" checked={terminator} onToggle={onToggleTerminator} />
        <Toggle label="Lite mode" checked={lite} onToggle={onToggleLite} />
        <Toggle label="GNSS interference" checked={interference} onToggle={onToggleInterference} />
      </div>
      {stats !== null && (
        <p className="mt-1 px-1 font-mono text-[11px] text-muted">
          Server at last snapshot: <span>{formatBudget(stats)}</span>
        </p>
      )}
      <LiveCoverage
        filteredCount={Object.values(counts).reduce((total, count) => total + count, 0)}
      />
      {error !== null && (
        <p role="alert" className="mt-1 px-1 text-xs text-critical">
          {error}
        </p>
      )}
    </section>
  );
}
