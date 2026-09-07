import type { MapState } from '@/lib/api/mapViews';

export function MapTimelineHeader({
  version,
  timeBasis,
}: {
  version: number;
  timeBasis: MapState['time_basis'];
}) {
  return (
    <header>
      <h2 className="text-lg font-semibold">Map and timeline</h2>
      <p className="mt-1 text-sm text-muted">
        Frozen evidence from version {version}.{' '}
        {timeBasis === 'publication'
          ? 'Publication dates describe reporting time, not necessarily when an event happened.'
          : 'Observations use acquisition dates; other reporting uses publication dates. Retrieval time is never substituted.'}{' '}
        Optional catalogue and local overlays remain separate from saved evidence.
      </p>
    </header>
  );
}
