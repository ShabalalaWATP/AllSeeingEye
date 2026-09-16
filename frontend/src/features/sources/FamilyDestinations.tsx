import { Link } from 'react-router';

import { MAP_GUIDE_PANEL, mapPanelHref } from '@/lib/mapLayerDirectory';

import { FAMILY_LABELS, type Family } from './catalogueEntries';

interface Destination {
  readonly to: string;
  readonly label: string;
}

/** Where each data family is actually used, so the catalogue is not a dead end. */
const DESTINATIONS: Record<Family, readonly Destination[]> = {
  feed: [
    { to: mapPanelHref(MAP_GUIDE_PANEL), label: 'See these layers on the map' },
    { to: '/trackers', label: 'Live monitor' },
  ],
  research: [
    { to: '/research', label: 'Start a piece of research' },
    { to: '/subscriptions', label: 'Follow a topic on a schedule' },
  ],
  camera_index: [{ to: mapPanelHref('CCTV'), label: 'Open cameras on the map' }],
  map_layer: [{ to: mapPanelHref(MAP_GUIDE_PANEL), label: 'Open the map guide' }],
  ukraine_dataset: [{ to: '/conflicts/ukraine', label: 'Ukraine war tracker' }],
  reference_dataset: [
    { to: '/trackers', label: 'Live monitor' },
    { to: mapPanelHref(MAP_GUIDE_PANEL), label: 'Open the map guide' },
  ],
};

function isFamily(value: string): value is Family {
  return value in DESTINATIONS;
}

/** Shown once the catalogue is narrowed to one family; nothing to offer otherwise. */
export function FamilyDestinations({ family }: { family: string }) {
  if (!isFamily(family)) return null;
  return (
    <nav
      aria-label={`Where ${FAMILY_LABELS[family]} appear`}
      className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border border-line/70 bg-surface/50 px-4 py-3"
    >
      <span className="text-xs text-muted">Where {FAMILY_LABELS[family].toLowerCase()} appear</span>
      {DESTINATIONS[family].map((destination) => (
        <Link
          key={destination.to}
          to={destination.to}
          className="min-h-11 rounded-md py-3 text-sm text-ember hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember"
        >
          {destination.label}
        </Link>
      ))}
    </nav>
  );
}
