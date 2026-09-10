import type { RfMapEstimate } from '@/lib/map/rfMap';
import { RfMapLegend } from './RfMapLegend';

export function RfReferenceControls({
  originPlaced,
  estimate,
  error,
  visible,
  onChange,
}: {
  originPlaced: boolean;
  estimate: RfMapEstimate | null;
  error: string | null;
  visible: boolean;
  onChange: (estimate: RfMapEstimate | null) => void;
}) {
  return (
    <div className="space-y-3 border-t border-line pt-3">
      {!originPlaced && (
        <p className="text-muted">Place a transmitter to show the estimate on the map.</p>
      )}
      {error && (
        <p role="status" className="text-amber-300">
          {error}
        </p>
      )}
      <button
        type="button"
        disabled={!estimate}
        onClick={() => onChange(estimate)}
        className="min-h-10 w-full rounded border border-cyan/40 bg-cyan/10 px-3 text-cyan disabled:opacity-40"
      >
        {visible ? 'Update map estimate' : 'Show estimate on map'}
      </button>
      {visible && (
        <button type="button" onClick={() => onChange(null)} className="min-h-9 w-full text-muted">
          Clear map estimate
        </button>
      )}
      <RfMapLegend terrain={false} />
      <p className="text-muted">
        The labelled boundary is the smaller of the ideal radio horizon and sensitivity distance.
        Red marks a receiver path beyond that limit. Terrain has not been checked. Changing radio
        settings or sites clears the previous estimate.
      </p>
    </div>
  );
}
