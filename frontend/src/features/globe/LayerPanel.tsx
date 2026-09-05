import type { Category, StoreStats } from '@/lib/api/eventSchemas';
import type { StreamStatus } from '@/lib/sse';

import { ConnectionStatus } from './ConnectionStatus';
import { CATEGORY_STYLES, ORDERED_CATEGORIES } from './layers/registry';

export interface LayerPanelProps {
  counts: Partial<Record<Category, number>>;
  hidden: readonly Category[];
  stats: StoreStats | null;
  status: StreamStatus;
  error: string | null;
  onToggle: (category: Category) => void;
}

const MEBIBYTE = 1_048_576;

export function formatBudget(stats: StoreStats): string {
  const used = (stats.estimated_bytes / MEBIBYTE).toFixed(1);
  const budget = Math.round(stats.budget_bytes / MEBIBYTE);
  return `${stats.total} events, ${used} of ${budget} MB`;
}

/** Per-category visibility switches with live counts, plus the store budget line. */
export function LayerPanel({ counts, hidden, stats, status, error, onToggle }: LayerPanelProps) {
  return (
    <section
      aria-label="Layers"
      className="absolute top-16 left-3 z-10 w-52 rounded-md border border-line bg-surface/90 p-2 backdrop-blur"
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
                className={`flex w-full items-center gap-2 rounded px-1.5 py-1 text-left text-sm transition-colors hover:bg-surface-2 ${
                  shown ? 'text-text' : 'text-muted'
                }`}
              >
                <span
                  aria-hidden="true"
                  className="inline-block h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: style.css, opacity: shown ? 1 : 0.3 }}
                />
                <span className="flex-1">{style.label}</span>{' '}
                <span className="font-mono text-xs text-muted tabular-nums">{counts[category] ?? 0}</span>
              </button>
            </li>
          );
        })}
      </ul>
      {stats !== null && (
        <p className="mt-1 px-1 font-mono text-[11px] text-muted">{formatBudget(stats)}</p>
      )}
      {error !== null && (
        <p role="alert" className="mt-1 px-1 text-xs text-critical">
          {error}
        </p>
      )}
    </section>
  );
}
