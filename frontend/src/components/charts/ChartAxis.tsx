/**
 * Axis labels drawn in HTML over or under a scaled SVG chart. SVG text shrinks with the
 * viewBox (a 640-unit chart at 320px renders 9-unit text at about 4px), whereas these
 * labels keep the 11px `text-2xs` size at any chart width. The chart's table view carries
 * the exact values, so the labels are hidden from assistive technology.
 */
export interface AxisTick {
  key: string | number;
  label: string;
  /** Position along the axis as a fraction of the chart, 0 to 1. */
  at: number;
}

const percent = (fraction: number) => `${(Math.min(1, Math.max(0, fraction)) * 100).toFixed(3)}%`;

/** Value labels that sit just above their gridlines, aligned to one edge of the plot. */
export function ValueAxisLabels({
  ticks,
  edge = 'right',
}: {
  ticks: readonly AxisTick[];
  edge?: 'left' | 'right';
}) {
  return (
    <div
      aria-hidden="true"
      data-chart-axis="value"
      className="pointer-events-none absolute inset-0 font-mono text-2xs leading-none text-muted"
    >
      {ticks.map((tick) => (
        <span
          key={tick.key}
          className={`absolute -translate-y-full pb-0.5 whitespace-nowrap ${
            edge === 'right' ? 'right-0' : 'left-0'
          }`}
          style={{ top: percent(tick.at) }}
        >
          {tick.label}
        </span>
      ))}
    </div>
  );
}

/** Category or date labels in a row beneath the plot; edge labels align inwards. */
export function CategoryAxisLabels({ ticks }: { ticks: readonly AxisTick[] }) {
  return (
    <div
      aria-hidden="true"
      data-chart-axis="category"
      className="relative h-4 font-mono text-2xs leading-4 text-muted"
    >
      {ticks.map((tick) => {
        const shift =
          tick.at <= 0.15 ? '' : tick.at >= 0.85 ? '-translate-x-full' : '-translate-x-1/2';
        return (
          <span
            key={tick.key}
            className={`absolute top-0 whitespace-nowrap ${shift}`}
            style={{ left: percent(tick.at) }}
          >
            {tick.label}
          </span>
        );
      })}
    </div>
  );
}
