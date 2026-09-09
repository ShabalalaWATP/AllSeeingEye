import type { RfAnalysis } from '@/lib/map/rfAnalysis';
import { RfTerrainProfileChart } from './RfTerrainProfileChart';
import { RfGroundwaveResults } from './RfGroundwaveResults';

const statusText = {
  clear: 'Sampled clearance passed',
  risk: 'Clearance or link margin at risk',
  blocked: 'Sampled terrain blocks line of sight',
  unknown: 'Terrain assessment incomplete',
};
export function RfAnalysisResults({ analysis }: { analysis: RfAnalysis }) {
  if (analysis.kind === 'hf-groundwave') return <RfGroundwaveResults analysis={analysis} />;
  if (analysis.kind === 'hf-skywave') {
    const { scenario } = analysis.estimate;
    return (
      <section
        aria-label="HF skywave scenario result"
        className="space-y-3 rounded-lg border border-indigo-300/30 bg-indigo-300/5 p-3"
      >
        <p className="text-indigo-200">Single-hop geometry scenario</p>
        <p className="font-mono text-lg">
          {scenario.compatible
            ? `${scenario.innerRadiusKm?.toFixed(0)}–${scenario.outerRadiusKm?.toFixed(0)} km`
            : 'No compatible hop in these assumptions'}
        </p>
        <p className="text-xs text-muted">
          The inner and outer rings show the selected virtual-layer and launch-angle scenario. They
          do not predict signal strength or reception. Power and mast height do not determine these
          rings; antenna patterns would be needed to derive launch angles.
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
      </section>
    );
  }
  const { terrain, elevations, input, plan } = analysis;
  const txGround = elevations.elevations_m[0];
  const rxGround = terrain.path ? elevations.elevations_m.at(-1) : undefined;
  return (
    <section aria-label="Terrain radio analysis" className="space-y-3">
      <div className="rounded-lg border border-cyan/25 bg-cyan/5 p-3">
        <p className="font-medium text-cyan">
          {terrain.path ? statusText[terrain.path.status] : 'Sampled terrain sectors'}
        </p>
        <div className="mt-2 grid grid-cols-2 gap-3 text-xs">
          <div>
            <p className="text-muted">TX ground elevation</p>
            <p className="font-mono">{txGround?.toFixed(1)} m</p>
            <p className="text-muted">+ {input.transmitHeightM} m antenna AGL</p>
            <p className="font-mono">
              {((txGround ?? 0) + input.transmitHeightM).toFixed(1)} m antenna elevation
            </p>
          </div>
          <div>
            {rxGround !== undefined ? (
              <>
                <p className="text-muted">RX ground elevation</p>
                <p className="font-mono">{rxGround.toFixed(1)} m</p>
                <p className="text-muted">+ {input.receiveHeightM} m antenna AGL</p>
                <p className="font-mono">
                  {(rxGround + input.receiveHeightM).toFixed(1)} m antenna elevation
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
        <p className="mt-2 text-[10px] text-muted">
          Elevations use the source sea-level datum. Grid spacing up to{' '}
          {elevations.resolution_m.toFixed(0)} m is not a height-accuracy guarantee.
        </p>
      </div>
      {terrain.path && (
        <>
          <RfTerrainProfileChart profile={terrain.path} />
          <dl className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <dt className="text-muted">Sampled diffraction loss</dt>
              <dd className="font-mono">
                {terrain.path.diffractionLossDb?.toFixed(1) ?? 'Unknown'} dB
              </dd>
            </div>
            <div>
              <dt className="text-muted">Modelled link margin</dt>
              <dd className="font-mono">{terrain.path.marginDb?.toFixed(1) ?? 'Unknown'} dB</dd>
            </div>
          </dl>
        </>
      )}
      <p className="text-xs text-muted">
        Cyan marks sampled clearance. Amber/orange marks clearance risk or obstruction; grey is
        unknown. Unfilled gaps have not been assessed.
      </p>
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
    </section>
  );
}
