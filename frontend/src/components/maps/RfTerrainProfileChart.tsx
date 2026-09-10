import type { RfTerrainProfile } from '@/lib/map/rfTerrainTypes';
import { RF_STATUS_CSS, rfPathSegmentStatus, rfPathSummary } from '@/lib/map/rfTerrainPresentation';

/** Side view in the effective-Earth frame used by the sampled clearance calculation. */
export function RfTerrainProfileChart({ profile }: { profile: RfTerrainProfile }) {
  if (profile.points.some((p) => p.elevationM === null || p.rayHeightM === null))
    return (
      <p className="text-muted">
        The profile contains missing elevations and cannot show clearance.
      </p>
    );
  const values = profile.points.flatMap((p) => [
    (p.elevationM ?? 0) + p.earthBulgeM,
    p.rayHeightM ?? 0,
    (p.rayHeightM ?? 0) - p.fresnel60M,
  ]);
  const low = Math.floor(Math.min(...values) - 10),
    high = Math.ceil(Math.max(...values) + 10);
  const x = (distance: number) => 36 + (268 * distance) / (profile.distanceKm * 1000);
  const y = (height: number) => 132 - (104 * (height - low)) / (high - low);
  const series = (value: (p: RfTerrainProfile['points'][number]) => number) =>
    profile.points.map((p) => `${x(p.distanceM).toFixed(2)},${y(value(p)).toFixed(2)}`).join(' ');
  const summary = rfPathSummary(profile);
  const obstruction = summary.firstBlocked ?? summary.firstRisk;
  const obstructionColour = summary.firstBlocked ? RF_STATUS_CSS.blocked : RF_STATUS_CSS.risk;
  return (
    <figure className="overflow-hidden rounded-lg border border-cyan/20 bg-black/40 p-2">
      <svg
        viewBox="0 0 320 158"
        className="w-full"
        role="img"
        aria-label="Terrain profile with radio line and lower 60 percent Fresnel boundary"
      >
        {[28, 80, 132].map((row) => (
          <line key={row} x1="36" x2="304" y1={row} y2={row} stroke="#ffffff15" />
        ))}
        <polygon
          points={`36,132 ${series((p) => (p.elevationM ?? 0) + p.earthBulgeM)} 304,132`}
          fill="#7f9caa30"
        />
        <polyline
          points={series((p) => (p.elevationM ?? 0) + p.earthBulgeM)}
          fill="none"
          stroke="#a3b8c4"
          strokeWidth="1.5"
        />
        <polyline
          points={series((p) => (p.rayHeightM ?? 0) - p.fresnel60M)}
          fill="none"
          stroke={RF_STATUS_CSS.risk}
          strokeDasharray="3 3"
        />
        <polyline
          points={series((p) => p.rayHeightM ?? 0)}
          fill="none"
          stroke="#02070c"
          strokeWidth="6"
        />
        {profile.points.map((point, index) => {
          const previous = profile.points[index - 1];
          if (!previous) return null;
          const status = rfPathSegmentStatus(profile, previous, point, summary);
          return (
            <line
              key={point.distanceM}
              data-ray-status={status}
              x1={x(previous.distanceM)}
              y1={y(previous.rayHeightM ?? 0)}
              x2={x(point.distanceM)}
              y2={y(point.rayHeightM ?? 0)}
              stroke={RF_STATUS_CSS[status]}
              strokeWidth="3"
            />
          );
        })}
        {obstruction && (
          <g>
            <line
              x1={x(obstruction.distanceM)}
              x2={x(obstruction.distanceM)}
              y1="28"
              y2="132"
              stroke={obstructionColour}
              strokeDasharray="3 3"
            />
            <circle
              cx={x(obstruction.distanceM)}
              cy={y(obstruction.rayHeightM ?? 0)}
              r="4"
              fill="#02070c"
              stroke={obstructionColour}
              strokeWidth="2"
            />
          </g>
        )}
        <g fill="#a0a6ae" fontSize="9" fontFamily="monospace">
          <text x="1" y="31">
            {high}m
          </text>
          <text x="1" y="134">
            {low}m
          </text>
          <text x="36" y="151">
            TX
          </text>
          <text x="304" y="151" textAnchor="end">
            RX · {profile.distanceKm.toFixed(1)} km
          </text>
        </g>
      </svg>
      <figcaption className="text-[10px] leading-relaxed text-muted">
        Grey: sampled terrain plus Earth curvature. Mint: clear direct ray. Amber: clearance or
        power risk, including the interval before a sampled intrusion. Red: obstructed direct ray.
        Dashed amber: lower 60% Fresnel boundary.
        {obstruction && (
          <span className="mt-1 block" style={{ color: obstructionColour }}>
            {summary.firstBlocked ? 'First sampled obstruction' : 'First sampled Fresnel intrusion'}{' '}
            at {(obstruction.distanceM / 1000).toFixed(2)} km from TX.
            {summary.firstBlocked &&
              ' Red beyond the marker means the direct ray stays obstructed, not zero reception.'}
          </span>
        )}
      </figcaption>
    </figure>
  );
}
