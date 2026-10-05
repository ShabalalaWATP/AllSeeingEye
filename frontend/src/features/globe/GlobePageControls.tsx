/** The map's tool rails and every panel they open, wired to the composed page model. */
import { dashboardCataloguePanels } from './dashboardCataloguePanels';
import { DashboardLayerRail } from './DashboardLayerRail';
import { eventControlPanels } from './eventControlPanels';
import { GlobeControls } from './GlobeControls';
import { liveViewPanels } from './liveViewPanels';
import { mapGuidePanel } from './MapGuidePanel';
import { MapNavigationTools } from './MapNavigationTools';
import { mapPlanningPanels } from './MapPlanningPanels';
import { mapReferencePanels } from './MapReferencePanels';
import { MapToolActivity } from './MapToolActivity';
import type { GlobePageModel } from './useGlobePage';
import type { GlobePanelRoute } from './useGlobePanelRoute';
import type { MapPanel } from './mapToolDefinitions';

export function GlobePageControls({
  page: { display, canvas, reference, events, sources, actions, liveViews, now },
  route,
  stylePanel,
}: {
  page: GlobePageModel;
  route: GlobePanelRoute;
  stylePanel: MapPanel;
}) {
  const { engine, supported, britishGrid, tools } = canvas;
  const { data, country, selectedId, quality, details, onJam, focus, selectTraffic } = events;
  const { radar, cyber, regions, infrastructure, cameras, figures, gnss, gnssFilters } = sources;
  const { technology, selectContext, selectSatellite, focusInfrastructure } = actions;
  return (
    <GlobeControls
      onActiveChange={(label) => {
        tools.activatePanel(label);
        if (label === 'Technology & communications') technology.activate();
      }}
      layers={(openPanel, activePanel) => (
        <DashboardLayerRail
          data={data}
          cyberCount={cyber.events.length}
          openPanel={openPanel}
          activePanel={activePanel}
          onTrafficSelect={selectTraffic}
          selectionDisabled={tools.picking}
        />
      )}
      navigation={<MapNavigationTools engine={engine} enabled={supported} />}
      activity={<MapToolActivity tools={tools} />}
      requestedPanel={route.requestedPanel}
      requestKey={route.requestKey}
      showRef={route.showPanel}
      onPanelChange={route.onPanelChange}
    >
      {(openPanel) => [
        mapGuidePanel(openPanel, {
          events: data,
          cameras,
          figures,
          regions,
          grid: britishGrid,
        }),
        dashboardCataloguePanels({
          data,
          infrastructure,
          focusInfrastructure,
          technology,
          onContextSelect: selectContext,
          onSatelliteSelect: selectSatellite,
          onTrafficSelect: selectTraffic,
          picking: tools.picking,
          engine,
          onJam,
          conflictOverview: { regions, onSelect: actions.regionSelection.focus },
          cyber: {
            cyber,
            onSelect: actions.cyberSelection.selectRecord,
            picking: tools.picking,
            radar,
          },
          gnss: {
            enabled: display.interference,
            data: gnss,
            filters: gnssFilters,
            selected: details?.kind === 'jam' ? details.cell : null,
          },
        }),
        mapReferencePanels({
          stylePanel,
          nation: {
            countries: reference.countries,
            value: country,
            onChange: reference.changeNation,
            error: reference.countriesError,
          },
          country: reference.nation
            ? {
                country: reference.nation,
                events: quality.filtered,
                selectedId,
                now,
                onSelect: focus,
              }
            : null,
          precision: {
            events: quality.visible,
            hidden: [],
            filter: quality.filter,
            onFilterChange: quality.setFilter,
            onSelect: focus,
          },
          grid: { grid: britishGrid, engine },
          cameras: { cameras, onSelect: actions.focusCamera },
          figures: { figures, onSelect: actions.focusFigure },
        }),
        mapPlanningPanels(tools, {
          open: openPanel,
          events: data.list,
          exportEvents: quality.filtered,
          onHighlight: focus,
          onNavigate: (center) => engine.flyTo({ center, zoom: 12 }),
        }),
        eventControlPanels(data, actions.networkSelection.selectRecord),
        liveViewPanels(liveViews),
      ]}
    </GlobeControls>
  );
}
