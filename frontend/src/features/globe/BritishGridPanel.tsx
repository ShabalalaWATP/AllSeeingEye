import { BNG_MIN_ZOOM, BNG_NOTE } from '@/lib/map/britishGrid';

export function BritishGridPanel({
  enabled,
  onToggle,
  onLocate,
  zoom,
}: {
  enabled: boolean;
  onToggle: () => void;
  onLocate: () => void;
  zoom: number;
}) {
  return (
    <div className="space-y-3 p-3 text-xs text-muted">
      <label className="flex items-center gap-2 text-text">
        <input type="checkbox" checked={enabled} onChange={onToggle} />
        Show British National Grid
      </label>
      <p>
        Great Britain and surrounding grid extent. 100 km lines, with 10 km lines when zoomed in.
        Move the pointer for eastings and northings.
      </p>
      {enabled && zoom < BNG_MIN_ZOOM && (
        <p role="status">Zoom in to see the grid, or locate Great Britain below.</p>
      )}
      <button
        type="button"
        onClick={onLocate}
        className="rounded border border-line px-3 py-2 text-text"
      >
        Locate Great Britain
      </button>
      <p>{BNG_NOTE}</p>
    </div>
  );
}
