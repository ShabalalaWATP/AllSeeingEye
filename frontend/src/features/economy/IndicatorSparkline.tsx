import type { EconomySeries } from '@/lib/api/economy';

export function IndicatorSparkline({ series }: { series: EconomySeries }) {
  const points = series.points.slice(-16);
  const values = points.flatMap((point) => (point.value === null ? [] : [point.value]));
  if (!values.length)
    return (
      <span className="mt-4 block h-12 border-b border-dashed border-line" aria-hidden="true" />
    );
  const low = Math.min(...values);
  const range = Math.max(...values) - low || 1;
  const x = (index: number) => 3 + (index * 194) / Math.max(1, points.length - 1);
  const y = (value: number) => 43 - ((value - low) / range) * 36;
  const path = points
    .map((point, index) => {
      if (point.value === null) return '';
      const previous = points[index - 1];
      const adjacent =
        previous && previous.value !== null && Number(point.date) - Number(previous.date) === 1;
      return `${adjacent ? 'L' : 'M'}${x(index)},${y(point.value)}`;
    })
    .join(' ');
  return (
    <svg viewBox="0 0 200 50" className="mt-3 h-12 w-full text-ember" aria-hidden="true">
      <path d={path} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      {points.map((point, index) =>
        point.value === null ? null : (
          <circle key={point.date} cx={x(index)} cy={y(point.value)} r="1.8" fill="currentColor" />
        ),
      )}
    </svg>
  );
}
