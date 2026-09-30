import { useState, type PointerEvent } from 'react';
import type { Position } from '@/lib/map/geoJsonTypes';
import type { RfTerrainProfile, RfTerrainProfilePoint } from '@/lib/map/rfTerrainTypes';
import { RF_STATUS_CSS, rfPathSegmentStatus, rfPathSummary } from '@/lib/map/rfTerrainPresentation';

type CompletePoint = RfTerrainProfilePoint & { elevationM: number; rayHeightM: number };

function hasHeights(point: RfTerrainProfilePoint): point is CompletePoint {
  return point.elevationM !== null && point.rayHeightM !== null;
}

/** Side view in the effective-Earth frame used by the sampled clearance calculation. */
export function RfTerrainProfileChart({
  profile,
  onProfilePoint,
}: {
  profile: RfTerrainProfile;
  onProfilePoint?: ((point: Position | null) => void) | undefined;
}) {
  const [selected, setSelected] = useState(0);
  const points = profile.points;
  const select = (index: number) => {
    const bounded = Math.max(0, Math.min(points.length - 1, index));
    setSelected(bounded);
    onProfilePoint?.(points[bounded]?.position ?? null);
  };
  if (!points.every(hasHeights))
    return (
      <p className="text-muted">
        The profile contains missing elevations and cannot show clearance.
      </p>
    );
  // The guard narrows every rendered sample; missing heights must never draw at zero.
  const focused = points[selected];
  const values = points.flatMap((p) => [
    p.elevationM + p.earthBulgeM,
    p.elevationM + p.earthBulgeM + (p.obstacleHeightM ?? 0),
    p.rayHeightM,
    p.rayHeightM - p.fresnel60M,
  ]);
  const low = Math.floor(Math.min(...values) - 10),
    high = Math.ceil(Math.max(...values) + 10);
  const x = (distance: number) => 36 + (268 * distance) / (profile.distanceKm * 1000);
  const y = (height: number) => 132 - (104 * (height - low)) / (high - low);
  const series = (value: (p: CompletePoint) => number) =>
    points.map((p) => `${x(p.distanceM).toFixed(2)},${y(value(p)).toFixed(2)}`).join(' ');
  const summary = rfPathSummary(profile);
  const obstruction = summary.firstBlocked ?? summary.firstRisk;
  const obstructionColour = summary.firstBlocked ? RF_STATUS_CSS.blocked : RF_STATUS_CSS.risk;
  const maximumObstacleM = Math.max(...points.map((point) => point.obstacleHeightM ?? 0));
  const inspect = (event: PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect();
    if (!box.width) return;
    const distance =
      ((((event.clientX - box.left) / box.width) * 320 - 36) / 268) * profile.distanceKm * 1000;
    let nearest = 0;
    points.forEach((point, index) => {
      if (
        Math.abs(point.distanceM - distance) <
        Math.abs((points[nearest]?.distanceM ?? Infinity) - distance)
      )
        nearest = index;
    });
    select(nearest);
  };
  return (
    <figure className="rf-profile overflow-hidden rounded-lg border border-cyan/20 bg-black/40 p-2">
      <svg
        onPointerMove={inspect}
        onPointerDown={inspect}
        viewBox="0 0 320 158"
        className="w-full"
        role="img"
        aria-label="Terrain profile with radio line and lower 60 percent Fresnel boundary"
      >
        <title>Sampled terrain and direct radio path</title>
        <desc>
          Grey shows source ground elevation with effective Earth curvature. The coloured ray shows
          clearance and reserve status. Amber dashed line is the lower Fresnel boundary.
          {maximumObstacleM > 0 &&
            ' Violet dashed line is the assumed obstacle screen, not measured terrain.'}
        </desc>
        {[28, 80, 132].map((row) => (
          <line key={row} x1="36" x2="304" y1={row} y2={row} stroke="#ffffff15" />
        ))}
        <polygon
          points={`36,132 ${series((p) => p.elevationM + p.earthBulgeM)} 304,132`}
          fill="#7f9caa30"
        />
        <polyline
          data-profile-series="terrain"
          points={series((p) => p.elevationM + p.earthBulgeM)}
          fill="none"
          stroke="#a3b8c4"
          strokeWidth="1.5"
        />
        {maximumObstacleM > 0 && (
          <polyline
            data-profile-series="assumed-obstacles"
            points={series((p) => p.elevationM + p.earthBulgeM + (p.obstacleHeightM ?? 0))}
            fill="none"
            stroke="#c4a7ff"
            strokeWidth="2"
            strokeDasharray="6 3"
          />
        )}
        <polyline
          points={series((p) => p.rayHeightM - p.fresnel60M)}
          fill="none"
          stroke={RF_STATUS_CSS.risk}
          strokeDasharray="3 3"
        />
        <polyline
          points={series((p) => p.rayHeightM)}
          fill="none"
          stroke="#02070c"
          strokeWidth="6"
        />
        {points.map((point, index) => {
          const previous = points[index - 1];
          if (!previous) return null;
          const status = rfPathSegmentStatus(profile, previous, point, summary);
          return (
            <line
              key={point.distanceM}
              data-ray-status={status}
              x1={x(previous.distanceM)}
              y1={y(previous.rayHeightM)}
              x2={x(point.distanceM)}
              y2={y(point.rayHeightM)}
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
        {focused && (
          <line
            x1={x(focused.distanceM)}
            x2={x(focused.distanceM)}
            y1="28"
            y2="132"
            stroke="#fff"
            strokeDasharray="2 2"
          />
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
      <label className="rf-field">
        <span>Inspect profile sample</span>
        <input
          type="range"
          min={0}
          max={points.length - 1}
          step={1}
          value={selected}
          onChange={(event) => select(Number(event.target.value))}
        />
      </label>
      {focused && (
        <p className="rf-help" aria-live="polite">
          {(focused.distanceM / 1000).toFixed(2)} km from TX · terrain{' '}
          {focused.elevationM.toFixed(1)} m · Fresnel clearance{' '}
          {focused.fresnelClearanceM?.toFixed(1) ?? 'unknown'} m. Position{' '}
          {focused.position[1].toFixed(5)}, {focused.position[0].toFixed(5)}.
        </p>
      )}
      <figcaption className="text-2xs leading-relaxed text-muted">
        Grey: sampled terrain plus Earth curvature. Mint: clear direct ray. Amber: clearance or
        power risk, including the interval before a sampled intrusion. Red: obstructed direct ray.
        Dashed amber: lower 60% Fresnel boundary.
        {maximumObstacleM > 0 && (
          <span className="mt-1 block text-violet-200">
            Violet dashed: assumed {maximumObstacleM.toFixed(1)} m obstacle screen above sampled
            ground. Buildings and trees have not been measured.
          </span>
        )}
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
