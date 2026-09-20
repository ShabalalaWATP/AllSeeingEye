import type { Category } from '@/lib/api/eventSchemas';
import type { MapLayerToggle } from '@/lib/mapLayerDirectory';

import type { useBritishGrid } from './useBritishGrid';
import type { useCameras } from './cameras/useCameras';
import type { useConflictRegions } from './useConflictRegions';
import type { useDashboardEvents } from './useDashboardEvents';
import type { useFigures } from './figures/useFigures';

/** The live layer state the guide switches, taken from the page that already holds it. */
export interface MapGuideSources {
  events: ReturnType<typeof useDashboardEvents>;
  cameras: ReturnType<typeof useCameras>;
  figures: ReturnType<typeof useFigures>;
  regions: ReturnType<typeof useConflictRegions>;
  grid: ReturnType<typeof useBritishGrid>;
}

export interface GuideSwitch {
  on: boolean;
  set: () => void;
}

/** Category layers plus the four reference layers whose state is owned by a page hook. */
export function guideSwitches(
  sources: MapGuideSources,
  hidden: readonly Category[],
  toggleCategory: (category: Category) => void,
): Partial<Record<MapLayerToggle, GuideSwitch>> {
  const { events, cameras, figures, regions, grid } = sources;
  const category = (value: Category): GuideSwitch => ({
    on: !hidden.includes(value),
    set: () => {
      toggleCategory(value);
    },
  });
  return {
    conflict: category('conflict'),
    disaster: category('disaster'),
    news: category('news'),
    cyber: category('cyber'),
    space: category('space'),
    fires: { on: events.fires.enabled, set: events.fires.toggleEnabled },
    cameras: {
      on: cameras.enabled,
      set: () => {
        cameras.setEnabled(!cameras.enabled);
      },
    },
    figures: {
      on: figures.enabled,
      set: () => {
        figures.setEnabled(!figures.enabled);
      },
    },
    regions: {
      on: regions.showRegions && !hidden.includes('conflict'),
      set: () => {
        const next = !regions.showRegions || hidden.includes('conflict');
        if (next && hidden.includes('conflict')) toggleCategory('conflict');
        regions.setShowRegions(next);
      },
    },
    grid: {
      on: grid.enabled,
      set: () => {
        grid.setEnabled(!grid.enabled);
      },
    },
  };
}
