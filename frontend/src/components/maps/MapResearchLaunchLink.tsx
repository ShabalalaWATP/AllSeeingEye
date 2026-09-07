import type { SavedMapView } from '@/lib/api/mapViews';

export function MapResearchLaunchLink({
  saved,
  changed,
}: {
  saved: SavedMapView | null;
  changed: boolean;
}) {
  if (!saved?.revision.state.aoi)
    return <p className="text-xs text-muted">Save a map revision with an area to research it.</p>;
  if (changed)
    return (
      <p className="text-xs text-muted">
        Apply or discard the area draft and save your area changes before starting research.
      </p>
    );
  return (
    <a
      className="inline-flex rounded border border-line px-4 py-3 text-sm hover:bg-surface-2"
      href={`/research?map_view=${encodeURIComponent(saved.view.id)}&map_revision=${encodeURIComponent(saved.revision.id)}`}
    >
      Research this saved area
    </a>
  );
}
