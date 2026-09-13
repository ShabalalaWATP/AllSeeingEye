import { SLOT_BG, formatCount, type ChartSlot } from './chartSlots';

export interface SharePart {
  key: string;
  label: string;
  value: number;
  slot: ChartSlot;
}

/** One full-width stacked bar for part-to-whole, with the legend carrying the values. */
export function ShareBar({ parts, label }: { parts: readonly SharePart[]; label: string }) {
  const total = parts.reduce((sum, part) => sum + part.value, 0);
  const shown = parts.filter((part) => part.value > 0);
  if (!total)
    return <p className="text-xs leading-5 text-muted">No records to apportion in this period.</p>;
  return (
    <figure className="space-y-3">
      <div
        role="img"
        aria-label={label}
        title={shown.map((part) => `${part.label} ${part.value}`).join(', ')}
        className="flex h-3 w-full gap-0.5 overflow-hidden rounded-sm"
      >
        {shown.map((part) => (
          <span
            key={part.key}
            className={`block h-full ${SLOT_BG[part.slot]}`}
            style={{ width: `${((part.value / total) * 100).toFixed(2)}%` }}
          />
        ))}
      </div>
      <figcaption>
        <ul className="grid gap-x-4 gap-y-1.5 text-xs sm:grid-cols-2">
          {shown.map((part) => (
            <li key={part.key} className="flex items-center justify-between gap-3">
              <span className="inline-flex min-w-0 items-center gap-2">
                <span
                  aria-hidden="true"
                  className={`size-2 shrink-0 rounded-sm ${SLOT_BG[part.slot]}`}
                />
                <span className="truncate">{part.label}</span>
              </span>
              <span className="shrink-0 font-mono text-[11px] text-muted tabular-nums">
                {formatCount(part.value)} · {Math.round((part.value / total) * 100)}%
              </span>
            </li>
          ))}
        </ul>
      </figcaption>
    </figure>
  );
}
