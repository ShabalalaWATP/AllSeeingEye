import { CategoryAxisLabels, ValueAxisLabels } from './ChartAxis';
import { SLOT_BG, SLOT_FILL, type ChartSlot } from './chartSlots';

export interface ColumnSeries {
  key: string;
  label: string;
  slot: ChartSlot;
  values: readonly number[];
}

const WIDTH = 640;
const BASE = 118;
// Axis labels are HTML beneath and over the plot, so the drawing stops just below the base.
const HEIGHT = BASE + 4;
const TOP = 10;
const GAP = 2;

function tick(max: number): number {
  const magnitude = 10 ** Math.floor(Math.log10(Math.max(1, max)));
  const step = [1, 2, 5, 10].map((n) => n * magnitude).find((n) => max / n <= 5) ?? magnitude;
  return step;
}

/** Daily stacked columns with a legend, hover titles and a table view of the same numbers. */
export function StackedColumns({
  days,
  series,
  label,
  unit = 'records',
}: {
  days: readonly string[];
  series: readonly ColumnSeries[];
  label: string;
  unit?: string;
}) {
  const totals = days.map((_, index) =>
    series.reduce((sum, row) => sum + (row.values[index] ?? 0), 0),
  );
  const max = Math.max(1, ...totals);
  const step = tick(max);
  const ceiling = Math.ceil(max / step) * step;
  const scale = (BASE - TOP) / ceiling;
  const slotWidth = WIDTH / Math.max(1, days.length);
  const barWidth = Math.min(24, slotWidth * 0.7);
  const labelEvery = days.length > 16 ? Math.ceil(days.length / 8) : days.length > 8 ? 2 : 1;
  const gridlines = Array.from({ length: Math.round(ceiling / step) + 1 }, (_, i) => i * step);
  const valueTicks = gridlines.map((value) => ({
    key: value,
    label: value.toLocaleString('en-GB'),
    at: (BASE - value * scale) / HEIGHT,
  }));
  const dayTicks = days.flatMap((day, index) =>
    index % labelEvery === 0
      ? [{ key: day, label: day.slice(5), at: (index * slotWidth + slotWidth / 2) / WIDTH }]
      : [],
  );
  return (
    <figure className="space-y-3">
      <div>
        <div className="relative">
          {/* A minimum height keeps gridline labels apart on narrow screens; the plot stretches. */}
          <svg
            viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
            preserveAspectRatio="none"
            role="img"
            aria-label={label}
            className="block h-auto min-h-36 w-full overflow-visible"
          >
            <title>{label}</title>
            {gridlines.map((value) => (
              <line
                key={value}
                x1="0"
                x2={WIDTH}
                y1={BASE - value * scale}
                y2={BASE - value * scale}
                className="stroke-line/60"
                strokeWidth="1"
                vectorEffect="non-scaling-stroke"
              />
            ))}
            {days.map((day, index) => {
              let offset = 0;
              const x = index * slotWidth + (slotWidth - barWidth) / 2;
              const summary = series
                .filter((row) => (row.values[index] ?? 0) > 0)
                .map((row) => `${row.label} ${row.values[index] ?? 0}`)
                .join(', ');
              return (
                <g key={day}>
                  <title>
                    {day}: {totals[index]} {unit}
                    {summary ? ` (${summary})` : ''}
                  </title>
                  <rect
                    x={index * slotWidth}
                    y={TOP - 6}
                    width={slotWidth}
                    height={BASE - TOP + 6}
                    className="fill-transparent hover:fill-surface-2/60"
                  />
                  {series.map((row) => {
                    const value = row.values[index] ?? 0;
                    if (value <= 0) return null;
                    const height = value * scale;
                    const y = BASE - offset - height;
                    offset += height;
                    const visible = Math.max(0, height - GAP);
                    return (
                      <rect
                        key={row.key}
                        x={x}
                        y={y + (height - visible)}
                        width={barWidth}
                        height={visible}
                        className={`${SLOT_FILL[row.slot]} pointer-events-none`}
                      />
                    );
                  })}
                </g>
              );
            })}
            <line
              x1="0"
              x2={WIDTH}
              y1={BASE}
              y2={BASE}
              className="stroke-line"
              strokeWidth="1"
              vectorEffect="non-scaling-stroke"
            />
          </svg>
          <ValueAxisLabels ticks={valueTicks} />
        </div>
        <CategoryAxisLabels ticks={dayTicks} />
      </div>
      <figcaption className="flex flex-wrap gap-x-4 gap-y-1 text-2xs text-muted">
        {series.length > 1 &&
          series.map((row) => (
            <span key={row.key} className="inline-flex items-center gap-1.5">
              <span aria-hidden="true" className={`size-2 rounded-sm ${SLOT_BG[row.slot]}`} />
              {row.label}
            </span>
          ))}
        {/* Colour identifies each series; the table carries the exact values. */}
        <span className="basis-full">The table view is the reference reading.</span>
      </figcaption>
      <details className="text-xs text-muted">
        <summary className="w-fit cursor-pointer hover:text-text">Table view</summary>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-left">
            <caption className="sr-only">{label}, as a table</caption>
            <thead>
              <tr>
                <th className="py-1 pr-3 font-medium">Date (UTC)</th>
                {series.map((row) => (
                  <th key={row.key} className="px-2 py-1 font-medium">
                    {row.label}
                  </th>
                ))}
                <th className="px-2 py-1 font-medium">Total</th>
              </tr>
            </thead>
            <tbody>
              {days.map((day, index) => (
                <tr key={day} className="border-t border-line/60">
                  <th className="py-1 pr-3 font-normal whitespace-nowrap">{day}</th>
                  {series.map((row) => (
                    <td key={row.key} className="px-2 py-1 font-mono tabular-nums">
                      {row.values[index] ?? 0}
                    </td>
                  ))}
                  <td className="px-2 py-1 font-mono tabular-nums">{totals[index]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}
