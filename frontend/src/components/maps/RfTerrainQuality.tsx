import type { RfAnalysis } from '@/lib/map/rfAnalysis';

type TerrainAnalysis = Extract<RfAnalysis, { kind: 'terrain' }>;
const metres = (value: number) =>
  `${value.toLocaleString('en-GB', { maximumFractionDigits: 1 })} m`;

/** Sampling density describes the evidence, never survey or propagation accuracy. */
export function RfTerrainQuality({ analysis }: { analysis: TerrainAnalysis }) {
  const { terrain, plan, elevations } = analysis;
  const gaps = plan.profiles.flatMap(({ distancesM }) =>
    distancesM.slice(1).flatMap((distance, index) => {
      const previous = distancesM[index];
      return previous === undefined ? [] : [distance - previous];
    }),
  );
  const maximumGapM = gaps.length ? Math.max(...gaps) : null;
  const firstTargets = plan.profiles.flatMap(({ distancesM }) =>
    distancesM[2] === undefined ? [] : [distancesM[2]],
  );
  return (
    <section
      aria-label="Terrain evidence quality"
      className="rf-result-quality space-y-3 rounded-lg border border-line p-3"
    >
      <p className="rf-result-kicker text-xs font-mono uppercase tracking-wider text-muted">
        Sampling & evidence
      </p>
      <dl className="rf-result-metrics grid grid-cols-2 gap-3 text-xs">
        <div className="rf-result-metric">
          <dt className="text-muted">Largest sample gap</dt>
          <dd className="font-mono text-base">
            {maximumGapM === null ? 'Unavailable' : metres(maximumGapM)}
          </dd>
        </div>
        <div className="rf-result-metric">
          <dt className="text-muted">Nominal DEM grid spacing</dt>
          <dd className="font-mono text-base">{metres(elevations.resolution_m)}</dd>
        </div>
      </dl>
      <p className="text-xs text-muted">
        {terrain.sampleCount} sampled positions. Grid spacing is not height accuracy; small ridges,
        buildings and trees can remain unresolved.
      </p>
      {terrain.kind === 'radial' && (
        <p className="text-xs text-muted">
          First assessed receiver:{' '}
          {firstTargets.length ? `${metres(Math.min(...firstTargets))} from TX` : 'unavailable'}.
          Nearby samples are closer together; distant samples are wider apart. Terrain between
          bearings is untested.
        </p>
      )}
      {maximumGapM !== null && maximumGapM > elevations.resolution_m * 2 && (
        <p className="rf-result-next-step text-xs text-amber-200">
          Sample gaps exceed the terrain grid spacing. Reduce the survey radius or analyse a
          point-to-point path through an area of interest for closer screening.
        </p>
      )}
      {terrain.missingSamples > 0 && (
        <p className="rf-result-next-step text-xs text-amber-200">
          {terrain.missingSamples} missing terrain samples. Affected paths are unknown; retry or
          choose another site before relying on this screen.
        </p>
      )}
      {terrain.belowSeaLevelSamples > 0 && (
        <p className="rf-result-next-step text-xs text-amber-200">
          Negative elevations may include bathymetry. Water-surface heights are unverified, so check
          over-water paths separately.
        </p>
      )}
    </section>
  );
}
