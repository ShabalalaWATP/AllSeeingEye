import type { RfTerrainProfile } from '@/lib/map/rfTerrainTypes';

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
          stroke="#fabb4c"
          strokeDasharray="3 3"
        />
        <polyline
          points={series((p) => p.rayHeightM ?? 0)}
          fill="none"
          stroke="#63e1eb"
          strokeWidth="2"
        />
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
        Grey: sampled terrain plus Earth curvature. Cyan: radio line. Dashed amber: lower 60%
        Fresnel boundary.
      </figcaption>
    </figure>
  );
}
