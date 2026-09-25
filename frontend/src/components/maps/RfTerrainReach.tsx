import { rfPathSummary, RF_STATUS_CSS } from '@/lib/map/rfTerrainPresentation';
import type { RfTerrainAnalysis } from '@/lib/map/rfTerrainTypes';

const stops = {
  clear: 'Survey limit reached',
  blocked: 'Direct path obstructed',
  risk: 'Fresnel / power risk',
  unknown: 'Missing terrain',
};

/** Distances describe sampled evidence, never an exact reception boundary. */
export function RfTerrainReach({ terrain }: { terrain: RfTerrainAnalysis }) {
  if (terrain.path) {
    const path = terrain.path;
    const { firstBlocked, firstRisk } = rfPathSummary(path);
    const planningMarginDb =
      path.planningMarginDb === undefined
        ? path.marginDb === null
          ? null
          : path.marginDb - (path.reserveDb ?? 0)
        : path.planningMarginDb;
    return (
      <div
        className="space-y-2 border-l-2 pl-3"
        style={{ borderColor: RF_STATUS_CSS[path.status] }}
      >
        <p className="font-mono text-lg">TX → RX · {path.distanceKm.toFixed(2)} km</p>
        {path.status === 'unknown' ? (
          <p>Missing terrain prevents a reach or obstruction estimate.</p>
        ) : firstBlocked ? (
          <>
            <p style={{ color: RF_STATUS_CSS.blocked }}>
              First sampled obstruction · {(firstBlocked.distanceM / 1000).toFixed(2)} km from TX
            </p>
            <p className="text-muted">
              The red tail marks the obstructed direct ray to RX. Diffraction may still carry a
              signal; red does not mean zero reception.
            </p>
          </>
        ) : (
          <p style={{ color: RF_STATUS_CSS[path.status] }}>
            {path.status === 'clear'
              ? 'Sampled clearance passes to the receiver.'
              : 'No sampled terrain crosses the direct ray, but this link is at risk.'}
          </p>
        )}
        {firstRisk && !firstBlocked && (
          <p>
            First sampled Fresnel restriction · {(firstRisk.distanceM / 1000).toFixed(2)} km from TX
          </p>
        )}
        {path.marginDb !== null && path.marginDb < 0 && (
          <p style={{ color: RF_STATUS_CSS.risk }}>
            Modelled power is {Math.abs(path.marginDb).toFixed(1)} dB below receiver sensitivity.
          </p>
        )}
        {path.marginDb !== null &&
          path.marginDb >= 0 &&
          planningMarginDb !== null &&
          planningMarginDb < 0 && (
            <p style={{ color: RF_STATUS_CSS.risk }}>
              Power exceeds receiver sensitivity, but falls {Math.abs(planningMarginDb).toFixed(1)}{' '}
              dB short of the selected planning reserve.
            </p>
          )}
        {path.status !== 'clear' && path.status !== 'unknown' && (
          <p className="rf-result-next-step text-xs text-muted">
            {firstBlocked || firstRisk
              ? 'Try a higher antenna or move a site clear of the marked obstruction, then recalculate.'
              : 'Check equipment sensitivity, power and cable losses against the intended operating mode, then recalculate.'}
          </p>
        )}
        <p className="text-2xs text-muted">
          Obstruction positions are coarse samples. Clear sections of this ray do not establish
          coverage for other receiver heights.
        </p>
      </div>
    );
  }
  const distances = terrain.radials.map((radial) => radial.clearDistanceKm);
  const minimum = distances.length ? Math.min(...distances) : 0;
  const maximum = distances.length ? Math.max(...distances) : 0;
  const passingBearings = distances.filter((distance) => distance > 0).length;
  return (
    <div className="space-y-3">
      <div className="border-l-2 border-cyan pl-3">
        <p className="text-muted">Last passing target by direction</p>
        <p
          className="font-mono text-2xl"
          style={{ color: passingBearings ? RF_STATUS_CSS.clear : RF_STATUS_CSS.risk }}
        >
          {passingBearings
            ? `${minimum.toFixed(2)}–${maximum.toFixed(2)} km`
            : 'No passing direction'}
        </p>
        <p className="mt-1 text-xs">
          {passingBearings} of {terrain.radials.length} bearings have a passing target.
        </p>
        <p className="mt-1 text-[11px] text-muted">
          Each bearing stops at its first failed or unknown target. A zero means no target passed.
          The survey limit is not a confirmed signal limit.
        </p>
        {passingBearings === 0 && (
          <p className="rf-result-next-step mt-2 text-xs text-amber-200">
            No sampled target passed. Reduce the survey radius to examine nearby coverage, or place
            a receiver at a specific site and analyse that path. Review antenna heights and the
            selected reserve before changing them.
          </p>
        )}
      </div>
      <details className="rounded-lg border border-line p-3">
        <summary className="cursor-pointer">Distances and limits by bearing</summary>
        <div className="mt-3 max-h-60 overflow-auto">
          <table className="w-full text-left text-2xs">
            <caption className="pb-2 text-left text-muted">
              Distances from TX. A failed target does not locate the obstructing ridge.
            </caption>
            <thead className="text-muted">
              <tr>
                <th scope="col">Bearing</th>
                <th scope="col">Last pass</th>
                <th scope="col">First stop / limit</th>
              </tr>
            </thead>
            <tbody>
              {terrain.radials.map((radial) => (
                <tr key={radial.bearingDegrees} className="border-t border-line align-top">
                  <th scope="row" className="py-2 font-mono font-normal">
                    {radial.bearingDegrees.toFixed(0)}°
                  </th>
                  <td className="py-2 font-mono">
                    {radial.clearDistanceKm > 0
                      ? `${radial.clearDistanceKm.toFixed(2)} km`
                      : 'No pass'}
                  </td>
                  <td className="py-2" style={{ color: RF_STATUS_CSS[radial.status] }}>
                    <span className="block font-mono">
                      {(radial.stopDistanceKm ?? terrain.maxDistanceKm).toFixed(2)} km
                    </span>
                    {stops[radial.status]}
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
