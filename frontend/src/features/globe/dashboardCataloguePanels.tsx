import { catalogueControlPanels } from './catalogueControlPanels';
import { trafficControlPanels } from './trafficControlPanels';
import type { useDashboardEvents } from './useDashboardEvents';
import type { GlobeEngineHandle } from './useGlobeEngine';

type Catalogue = Parameters<typeof catalogueControlPanels>[0];
type Traffic = Parameters<typeof trafficControlPanels>[0];

/** Apply the same live scope and interaction guard across category and traffic panels. */
export function dashboardCataloguePanels({
  data,
  infrastructure,
  focusInfrastructure,
  conflictOverview,
  cyber,
  gnss,
  onJam,
  engine,
  picking,
  onContextSelect,
  onSatelliteSelect,
  onTrafficSelect,
}: {
  data: ReturnType<typeof useDashboardEvents>;
  infrastructure: Catalogue['infrastructure'];
  focusInfrastructure: Catalogue['focusInfrastructure'];
  conflictOverview: Catalogue['conflictOverview'];
  cyber: Catalogue['cyber'];
  gnss: Omit<Catalogue['gnss'], 'onSelect' | 'selectionDisabled'>;
  onJam: Catalogue['gnss']['onSelect'];
  engine: GlobeEngineHandle;
  picking: boolean;
  onContextSelect: Catalogue['onContextSelect'];
  onSatelliteSelect: Catalogue['onSatelliteSelect'];
  onTrafficSelect: Traffic['onSelect'];
}) {
  return [
    ...catalogueControlPanels({
      infrastructure,
      focusInfrastructure,
      conflictOverview,
      cyber,
      fires: data.fires,
      news: {
        filters: data.news,
        country: data.country,
        windowHours: data.windowHours,
        onSelect: onContextSelect,
      },
      onContextSelect,
      onSatelliteSelect,
      satellites: data.satellites,
      conflicts: data.conflicts,
      hazards: data.hazards,
      country: data.country,
      selectedId: data.selectedId,
      qualityFilter: data.quality.filter,
      gnss: {
        ...gnss,
        selectionDisabled: picking,
        onSelect: (cell) => {
          if (picking) return;
          onJam(cell);
          engine.flyTo({ center: [cell.lon, cell.lat], zoom: 6 });
        },
      },
    }),
    ...trafficControlPanels({
      events: data.scoped,
      observations: data.observations,
      onSelect: onTrafficSelect,
      selectionDisabled: picking,
      country: data.country,
      onContextSelect,
      qualityFilter: data.quality.filter,
      available: Object.fromEntries(
        (data.stats?.per_category ?? []).flatMap((item) =>
          item.category === 'aviation'
            ? [['aircraft', item.count]]
            : item.category === 'maritime'
              ? [['vessels', item.count]]
              : [],
        ),
      ),
    }),
  ];
}
