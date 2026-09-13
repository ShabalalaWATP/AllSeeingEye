import { SLOT_BG, formatCount, type ChartSlot } from './chartSlots';

export interface BarRow {
  key: string;
  label: string;
  value: number;
  /** Optional secondary text after the label, in muted ink. */
  note?: string | undefined;
  slot?: ChartSlot;
}

/**
 * Horizontal bars with the value at the tip. One hue per list by default; a row
 * supplies its own slot only when the rows are distinct entities in a legend.
 */
export function BarList({
  rows,
  label,
  slot = 1,
  emptyText = 'No records in this period.',
  onSelect,
}: {
  rows: readonly BarRow[];
  label: string;
  slot?: ChartSlot;
  emptyText?: string;
  onSelect?: ((key: string) => void) | undefined;
}) {
  const max = Math.max(1, ...rows.map((row) => row.value));
  if (!rows.length) return <p className="text-xs leading-5 text-muted">{emptyText}</p>;
  return (
    <ul aria-label={label} className="space-y-2">
      {rows.map((row) => {
        const width = `${Math.max(1.5, (row.value / max) * 100).toFixed(1)}%`;
        const body = (
          <>
            <span className="flex items-baseline justify-between gap-3 text-xs">
              <span className="min-w-0 truncate text-text">
                {row.label}
                {row.note && <span className="ml-2 text-muted">{row.note}</span>}
              </span>
              <span className="shrink-0 font-mono text-[11px] text-muted tabular-nums">
                {formatCount(row.value)}
              </span>
            </span>
            <span className="mt-1 block h-2 w-full rounded-r-sm bg-surface-2">
              <span
                className={`block h-2 rounded-r-sm ${SLOT_BG[row.slot ?? slot]}`}
                style={{ width }}
              />
            </span>
          </>
        );
        return (
          <li key={row.key} title={`${row.label}: ${row.value.toLocaleString('en-GB')}`}>
            {onSelect ? (
              <button
                type="button"
                onClick={() => onSelect(row.key)}
                className="block w-full rounded-md px-1 py-1 text-left hover:bg-surface"
              >
                {body}
              </button>
            ) : (
              <div className="px-1 py-1">{body}</div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
