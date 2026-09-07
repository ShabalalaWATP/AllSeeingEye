import { Button } from '@/components/ui/Button';
import type { MapState } from '@/lib/api/mapViews';

export function MapDisplayVersionNotice({
  version,
  onUpgrade,
}: {
  version: MapState['display_transform'];
  onUpgrade: () => void;
}) {
  if (version !== 'ase-geojson-display-v1') return null;
  return (
    <div className="space-y-2 text-xs text-muted">
      <p>
        This saved map keeps its original point-only evidence display. Source footprints can be
        included in a new revision.
      </p>
      <Button variant="secondary" onClick={onUpgrade}>
        Include source footprints
      </Button>
      <p>Save a new revision to retain this change.</p>
    </div>
  );
}
