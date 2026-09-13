import { SLOT_FILL, SLOT_STROKE, type ChartSlot } from './chartSlots';

const WIDTH = 120;
const HEIGHT = 34;
const PAD = 4;

/** A small trend line with a wash beneath it and the latest point marked. */
export function Sparkline({
  values,
  slot = 1,
  label,
  className = '',
}: {
  values: readonly number[];
  slot?: ChartSlot;
  label: string;
  className?: string;
}) {
  const max = Math.max(1, ...values);
  const step = values.length > 1 ? (WIDTH - PAD * 2) / (values.length - 1) : 0;
  const points = values.map((value, index) => ({
    x: PAD + index * step,
    y: HEIGHT - PAD - (value / max) * (HEIGHT - PAD * 2),
  }));
  const line = points.map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(' ');
  const last = points.at(-1);
  const first = points[0];
  const area =
    first && last
      ? `M${first.x.toFixed(1)},${HEIGHT - PAD} L${line.replace(/ /g, ' L')} L${last.x.toFixed(1)},${HEIGHT - PAD} Z`
      : '';
  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      role="img"
      aria-label={label}
      preserveAspectRatio="none"
      className={`h-9 w-full overflow-visible ${className}`}
    >
      <title>{label}</title>
      {values.length > 1 && (
        <>
          <path d={area} className={`${SLOT_FILL[slot]} opacity-10`} />
          <polyline
            points={line}
            fill="none"
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
            vectorEffect="non-scaling-stroke"
            className={SLOT_STROKE[slot]}
          />
        </>
      )}
      {last && (
        <>
          <circle cx={last.x} cy={last.y} r="5" className="fill-surface" />
          <circle cx={last.x} cy={last.y} r="3.5" className={SLOT_FILL[slot]} />
        </>
      )}
    </svg>
  );
}
