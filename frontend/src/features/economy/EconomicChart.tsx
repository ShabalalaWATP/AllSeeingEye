import { useId, useState } from 'react';
import type { EconomySeries } from '@/lib/api/economy';
import { formatEconomicValue } from './economyPresentation';

/** Small bounded official series. Missing observations split the line, never become zero. */
export function EconomicChart({ series }: { series: EconomySeries }) {
  const [selected, setSelected] = useState<number | null>(null);
  const id = useId();
  const points = series.points;
  const values = points.flatMap((point) => (point.value === null ? [] : [point.value]));
  if (!values.length)
    return (
      <div className="flex min-h-64 items-center justify-center border-y border-dashed border-line px-6 text-center text-sm text-muted">
        No published observations are available for this series.
      </div>
    );
  const min = Math.min(...values),
    max = Math.max(...values);
  // Cross-rate division can differ by a few floating-point ULPs even when the
  // underlying ratio is constant. Do not magnify that noise into visible swings.
  const magnitude = Math.max(Math.abs(min), Math.abs(max), 1);
  const range = max - min;
  const margin = (range > magnitude * Number.EPSILON * 16 ? range : magnitude) * 0.12;
  const low = min - margin,
    high = max + margin;
  const x = (index: number) => 84 + (index * 708) / Math.max(1, points.length - 1);
  const y = (value: number) => 245 - ((value - low) / (high - low)) * 205;
  const path = points
    .map((point, index) => {
      if (point.value === null) return '';
      const previous = points[index - 1];
      const connected = previous !== undefined && previous.value !== null;
      return `${connected ? 'L' : 'M'}${x(index)},${y(point.value)}`;
    })
    .join(' ');
  const activeIndex =
    selected !== null && selected < points.length
      ? selected
      : points.findLastIndex((point) => point.value !== null);
  const focused = points[activeIndex];
  return (
    <div className="space-y-3">
      <div className="flex items-baseline justify-between gap-4 font-mono">
        <span className="text-sm text-muted">{focused?.date ?? 'Select an observation'}</span>
        <output
          aria-label="Selected observation value"
          className="text-xl tracking-tight text-text"
        >
          {formatEconomicValue(focused?.value ?? null, series.unit)}
        </output>
      </div>
      <svg
        viewBox="0 0 840 285"
        role="img"
        aria-labelledby={`${id}-title ${id}-desc`}
        className="w-full overflow-visible text-ember"
      >
        <title id={`${id}-title`}>{series.name} history</title>
        <desc id={`${id}-desc`}>
          Published {series.frequency} observations. Missing data creates gaps. Exact values are
          available in the table below.
        </desc>
        {[0, 1, 2, 3].map((tick) => {
          const value = low + ((high - low) * tick) / 3;
          return (
            <g key={tick}>
              <line
                x1="84"
                x2="802"
                y1={y(value)}
                y2={y(value)}
                className="stroke-line"
                strokeDasharray="3 5"
              />
              <text
                x="72"
                y={y(value) + 4}
                textAnchor="end"
                className="fill-muted font-mono text-[10px]"
              >
                {formatEconomicValue(value, series.unit)}
              </text>
            </g>
          );
        })}
        <path
          d={path}
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {points.map((point, index) =>
          point.value === null ? null : (
            <circle
              key={point.date}
              cx={x(index)}
              cy={y(point.value)}
              r={activeIndex === index ? 5 : 2.5}
              fill="currentColor"
            >
              <title>
                {point.date}: {formatEconomicValue(point.value, series.unit)}
              </title>
            </circle>
          ),
        )}
        {selected !== null && points[selected] && (
          <line
            x1={x(selected)}
            x2={x(selected)}
            y1="24"
            y2="245"
            stroke="currentColor"
            strokeOpacity="0.35"
            strokeDasharray="4 4"
          />
        )}
        {[0, Math.floor((points.length - 1) / 2), points.length - 1]
          .filter((n, i, all) => all.indexOf(n) === i)
          .map((index) => (
            <text
              key={index}
              x={x(index)}
              y="276"
              textAnchor="middle"
              className="fill-muted font-mono text-[10px]"
            >
              {points[index]?.date}
            </text>
          ))}
      </svg>
      <label className="flex items-center gap-4 text-xs text-muted">
        <span className="shrink-0">Explore dates</span>
        <input
          aria-label={`Explore ${series.name} observations`}
          type="range"
          min="0"
          max={Math.max(0, points.length - 1)}
          value={activeIndex}
          onChange={(event) => setSelected(Number(event.target.value))}
          className="w-full accent-ember"
        />
      </label>
      <details className="text-xs text-muted">
        <summary className="w-fit cursor-pointer py-2 hover:text-text">View data table</summary>
        <div className="max-h-56 overflow-auto">
          <table className="w-full text-left font-mono">
            <caption className="sr-only">
              {series.name} observations, {series.unit}
            </caption>
            <thead>
              <tr>
                <th className="py-2">Period</th>
                <th className="py-2">Value</th>
              </tr>
            </thead>
            <tbody>
              {points.map((point) => (
                <tr key={point.date} className="border-t border-line">
                  <td className="py-2">{point.date}</td>
                  <td>
                    {point.value === null
                      ? 'Not available'
                      : new Intl.NumberFormat('en-GB', { maximumFractionDigits: 20 }).format(
                          point.value,
                        )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
