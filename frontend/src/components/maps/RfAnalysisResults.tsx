import type { Position } from '@/lib/map/geoJsonTypes';
import type { RfAnalysis } from '@/lib/map/rfAnalysis';
import { RfTerrainProfileChart } from './RfTerrainProfileChart';
import { RfGroundwaveResults } from './RfGroundwaveResults';
import { RfMapLegend } from './RfMapLegend';
import { RfTerrainReach } from './RfTerrainReach';
import { RfTerrainBudget } from './RfTerrainBudget';
import { RfTerrainQuality } from './RfTerrainQuality';
import { RfLinkAdvice } from './RfLinkAdvice';
import { RF_STATUS_CSS } from '@/lib/map/rfTerrainPresentation';
import { analysisExplanation } from '@/lib/map/rfResultExplanation';
import { RfResultSummary } from './RfResultSummary';
import { RfEngineeringDetails } from './RfEngineeringDetails';

const statusText = {
  clear: 'Sampled clearance passed',
  risk: 'Clearance or link margin at risk',
  blocked: 'Sampled terrain blocks line of sight',
  unknown: 'Terrain assessment incomplete',
};
export function RfAnalysisResults({
  analysis,
  onProfilePoint,
  bubble = false,
}: {
  analysis: RfAnalysis;
  onProfilePoint?: ((point: Position | null) => void) | undefined;
  bubble?: boolean;
}) {
  if (analysis.kind === 'hf-groundwave') return <RfGroundwaveResults analysis={analysis} />;
  if (analysis.kind === 'hf-skywave') {
    const { scenario } = analysis.estimate;
    return (
      <section aria-label="HF skywave scenario result" className="space-y-3">
        <RfResultSummary value={analysisExplanation(analysis)} />
        <p className="text-sm text-muted">Illustrative travel distance</p>
        <p className="font-mono text-lg">
          {scenario.compatible
            ? `${scenario.innerRadiusKm?.toFixed(0)}–${scenario.outerRadiusKm?.toFixed(0)} km`
            : 'No compatible hop in these assumptions'}
        </p>
        <RfEngineeringDetails>
          <p className="text-indigo-200">Single-hop geometry scenario</p>
          <p className="text-xs text-muted">
            The inner and outer rings show the selected virtual-layer and launch-angle scenario.
            They do not predict signal strength or reception. Power and mast height do not determine
            these rings; antenna patterns would be needed to derive launch angles.
          </p>
          <p className="text-xs text-muted">{scenario.assumptions}</p>
          <a
            href="https://www.sws.bom.gov.au/Educational/5/2/2"
            target="_blank"
            rel="noreferrer"
            className="text-xs text-cyan underline"
          >
            HF propagation reference
          </a>
        </RfEngineeringDetails>
      </section>
    );
  }
  const { terrain, elevations, input, plan } = analysis;
  const txGround = terrain.path ? terrain.path.points[0]?.elevationM : elevations.elevations_m[0];
  const rxGround = terrain.path?.points.at(-1)?.elevationM;
  const headlineStatus =
    terrain.path?.status ??
    (terrain.radials.some((radial) => radial.clearDistanceKm > 0) ? 'clear' : 'unknown');
  return (
    <section aria-label="Terrain radio analysis" className="space-y-3">
      <RfResultSummary value={analysisExplanation(analysis)} />
      <RfLinkAdvice analysis={analysis} />
      {terrain.path && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium">Terrain along the path</h3>
          <p className="text-xs text-muted">
            Read from the transmitter on the left to the receiver on the right. Grey shows the
            ground. The dashed amber line marks the lower edge of the space the radio signal needs
            around its direct path. Select a point to inspect its values.
          </p>
          <RfTerrainProfileChart profile={terrain.path} onProfilePoint={onProfilePoint} />
        </div>
      )}
      <RfMapLegend />
      <p className="text-xs text-muted">
        Grey and unfilled areas have not been assessed. Red marks an obstructed direct path, not
        necessarily no reception.
      </p>
      <RfEngineeringDetails>
        <div className="rf-result-summary space-y-3">
          <p className="rf-result-kicker text-xs font-mono uppercase tracking-wider text-muted">
            {terrain.path ? 'Point-to-point terrain screen' : '360° terrain screen'}
          </p>
          <p className="text-lg font-medium" style={{ color: RF_STATUS_CSS[headlineStatus] }}>
            {terrain.path ? statusText[terrain.path.status] : 'Sampled terrain sectors'}
          </p>
        </div>
        <RfTerrainReach terrain={terrain} />
        {terrain.path && <RfTerrainBudget profile={terrain.path} />}
        <div className="border-y border-line py-3">
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <p className="text-muted">TX ground elevation</p>
              <p className="font-mono">
                {txGround == null ? 'Unknown' : `${txGround.toFixed(1)} m`}
              </p>
              <p className="text-muted">+ {input.transmitHeightM} m antenna AGL</p>
              <p className="font-mono">
                {txGround == null
                  ? 'Antenna elevation unknown'
                  : `${(txGround + input.transmitHeightM).toFixed(1)} m antenna elevation`}
              </p>
            </div>
            <div>
              {terrain.path ? (
                <>
                  <p className="text-muted">RX ground elevation</p>
                  <p className="font-mono">
                    {rxGround == null ? 'Unknown' : `${rxGround.toFixed(1)} m`}
                  </p>
                  <p className="text-muted">+ {input.receiveHeightM} m antenna AGL</p>
                  <p className="font-mono">
                    {rxGround == null
                      ? 'Antenna elevation unknown'
                      : `${(rxGround + input.receiveHeightM).toFixed(1)} m antenna elevation`}
                  </p>
                </>
              ) : (
                <>
                  <p className="text-muted">Survey radius</p>
                  <p className="font-mono">{terrain.maxDistanceKm} km</p>
                  <p className="text-muted">
                    {terrain.radials.length} bearings, {input.receiveHeightM} m receiver AGL
                  </p>
                </>
              )}
            </div>
          </div>
          <p className="mt-2 text-2xs text-muted">
            Elevations use the source sea-level datum. Antenna heights are above local ground.
            Effective Earth factor k={(terrain.engineering?.earthFactor ?? 4 / 3).toFixed(3)}.
            Assumed obstacle screen: {(terrain.engineering?.obstacleHeightM ?? 0).toFixed(1)} m
            above interior ground samples.
          </p>
        </div>
        <RfTerrainQuality analysis={analysis} />
        <p className="text-xs text-muted">
          Mint marks sampled clearance; amber is risk and red is an obstructed direct path. Grey and
          unfilled gaps have not been assessed. Passing a sampled screen does not guarantee
          reception.
        </p>
        {terrain.kind === 'radial' && bubble && (
          <p className="text-xs text-muted">
            The shaded bubble interpolates only to the shorter passing distance of adjacent
            bearings. Terrain between bearings has not been sampled, so the footprint is
            illustrative.
          </p>
        )}
        <details className="rounded-lg border border-line p-3 text-xs">
          <summary className="cursor-pointer">Terrain source and model limits</summary>
          <p className="mt-2 text-muted">
            {terrain.sampleCount} samples over {plan.maxDistanceKm.toFixed(1)} km. A narrow ridge
            between samples can be missed.
          </p>
          <ul className="mt-2 list-disc space-y-2 pl-4 text-muted">
            {terrain.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
          <p className="mt-2 text-muted">{elevations.limitations}</p>
          <p className="mt-2 text-muted">{elevations.attribution}</p>
          <a
            href={elevations.attribution_url}
            target="_blank"
            rel="noreferrer"
            className="mt-2 block text-cyan underline"
          >
            Terrain data sources and attribution
          </a>
          <a
            href="https://www.itu.int/rec/R-REC-P.526/en"
            target="_blank"
            rel="noreferrer"
            className="mt-2 block text-cyan underline"
          >
            ITU-R P.526 diffraction reference
          </a>
        </details>
      </RfEngineeringDetails>
    </section>
  );
}
