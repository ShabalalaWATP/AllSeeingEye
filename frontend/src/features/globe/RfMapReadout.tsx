import { memo } from 'react';
import type { RfAnalysis } from '@/lib/map/rfAnalysis';
import type { RfMapEstimate } from '@/lib/map/rfMap';
import { rfPathSummary } from '@/lib/map/rfTerrainPresentation';
import { RfMapLegend } from '@/components/maps/RfMapLegend';

/** A compact key remains available when the planning panel is closed. No timers. */
export const RfMapReadout = memo(function RfMapReadout({
  analysis,
  estimate,
}: {
  analysis: RfAnalysis | null;
  estimate: RfMapEstimate | null;
}) {
  const terrain = analysis?.kind === 'terrain' ? analysis.terrain : null;
  if (!terrain && !estimate) return null;
  const path = terrain?.path;
  const blocked = path ? rfPathSummary(path).firstBlocked : null;
  const label = estimate
    ? `Ideal limit · ${estimate.radiusKm.toFixed(2)} km`
    : path
      ? blocked
        ? `Obstruction sample · ${(blocked.distanceM / 1000).toFixed(2)} km`
        : `Receiver · ${path.distanceKm.toFixed(2)} km · ${path.status === 'clear' ? 'sampled pass' : path.status}`
      : '360° terrain estimate';
  return (
    <details className="absolute bottom-24 left-1/2 z-10 w-max max-w-[calc(100%-9rem)] -translate-x-1/2 rounded-lg border border-white/20 bg-black/90 p-2 text-text">
      <summary className="cursor-pointer text-[11px] marker:text-cyan">
        <span className="font-mono">RF · {label}</span>
      </summary>
      <div className="mt-2 max-w-72 border-t border-line pt-2">
        <RfMapLegend terrain={!!terrain} />
        <p className="mt-2 text-[10px] text-muted">
          {terrain
            ? 'Sampled estimate, not measured reception. Shaded gaps are illustrative.'
            : 'Ideal reference only. Terrain has not been checked.'}
        </p>
      </div>
    </details>
  );
});
