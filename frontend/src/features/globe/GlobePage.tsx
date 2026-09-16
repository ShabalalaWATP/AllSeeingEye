/** Full-canvas globe with on-demand layer and measurement tools. */
import { useSearchParams } from 'react-router';

import { readMapPanel } from '@/lib/mapLayerDirectory';

import { SavedMapAreaNotice } from './SavedMapAreaNotice';
import { GlobeInspectors } from './GlobeInspectors';
import { MapCanvas } from './MapCanvas';
import { MaritimeAttribution } from './MaritimeAttribution';
import { dashboardCataloguePanels } from './dashboardCataloguePanels';
import { eventControlPanels } from './eventControlPanels';
import { MapStatusReadouts } from './MapStatusReadouts';
import { GlobeControls } from './GlobeControls';
import { DashboardLayerRail } from './DashboardLayerRail';
import { MapNavigationTools } from './MapNavigationTools';
import { ModeToolbar } from './ModeToolbar';
import { mapPlanningPanels } from './MapPlanningPanels';
import { mapReferencePanels } from './MapReferencePanels';
import { mapGuidePanel } from './MapGuidePanel';
import { useGlobePage } from './useGlobePage';
import './dashboard.css';

export { FOCUS_ZOOM } from './useMapFocus';
export default function GlobePage() {
  const {
    display: {
      mode,
      setMode,
      baseLayer,
      setBaseLayer,
      terminator,
      toggleTerminator,
      lite,
      toggleLite,
      interference,
      opsRoom,
    },
    canvas: { containerRef, supported, engine, britishGrid, tools, savedArea },
    reference: {
      osMaps,
      osLoading,
      osError,
      recheckOs,
      countries,
      countriesError,
      changeNation,
      nation,
    },
    events: {
      data,
      hidden,
      country,
      selectedId,
      selected,
      quality,
      storySize,
      details,
      pickableEvents,
      choose,
      close,
      onJam,
      focus,
      selectTraffic,
    },
    sources: {
      radar,
      network,
      news,
      cyber,
      regions,
      infrastructure,
      cameras,
      figures,
      context,
      gnss,
      gnssFilters,
    },
    actions: {
      technology,
      selectContext,
      selectSatellite,
      focusInfrastructure,
      focusCamera,
      focusFigure,
      regionSelection,
      cyberSelection,
      networkSelection,
    },
    now,
  } = useGlobePage();
  const [params] = useSearchParams();
  const requestedPanel = readMapPanel(params);
  return (
    <div className="globe-dashboard absolute inset-0 bg-ground">
      <MapCanvas containerRef={containerRef} supported={supported} mode={mode} engine={engine} />
      {!opsRoom && <ModeToolbar mode={mode} onChange={setMode} />}
      {!opsRoom && <SavedMapAreaNotice area={savedArea} />}
      <MaritimeAttribution events={quality.filtered} hidden={hidden.includes('maritime')} />
      {!opsRoom && (
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
          initial={requestedPanel}
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
              conflictOverview: { regions, onSelect: regionSelection.focus },
              cyber: {
                cyber,
                onSelect: cyberSelection.selectRecord,
                picking: tools.picking,
                radar,
              },
              gnss: {
                enabled: interference,
                data: gnss,
                filters: gnssFilters,
                selected: details?.kind === 'jam' ? details.cell : null,
              },
            }),
            mapReferencePanels({
              display: {
                terminator,
                lite,
                onToggleTerminator: toggleTerminator,
                onToggleLite: toggleLite,
              },
              base: {
                initialExpanded: true,
                value: baseLayer,
                osAvailable: osMaps,
                osChecking: osLoading,
                osError,
                onCheckOs: recheckOs,
                onChange: setBaseLayer,
              },
              nation: { countries, value: country, onChange: changeNation, error: countriesError },
              country: nation
                ? { country: nation, events: quality.filtered, selectedId, now, onSelect: focus }
                : null,
              precision: {
                events: quality.visible,
                hidden: [],
                filter: quality.filter,
                onFilterChange: quality.setFilter,
                onSelect: focus,
              },
              grid: { grid: britishGrid, engine },
              cameras: { cameras, onSelect: focusCamera },
              figures: { figures, onSelect: focusFigure },
            }),
            mapPlanningPanels(tools),
            eventControlPanels(data, networkSelection.selectRecord),
          ]}
        </GlobeControls>
      )}
      <MapStatusReadouts
        tools={tools}
        engine={engine}
        supported={supported}
        opsRoom={opsRoom}
        bng={britishGrid.enabled}
      />
      {!opsRoom && !tools.picking && (
        <GlobeInspectors
          radar={radar}
          network={{ selected: network.selected, onClose: network.close }}
          news={{ state: news, onSelect: selectContext }}
          cyber={{ state: cyber, onSelect: cyberSelection.selectRecord }}
          regions={regions}
          infrastructure={infrastructure}
          cameras={cameras}
          figures={figures}
          eventDetails={{
            selected: selected ?? context.event,
            storySize,
            details,
            events: pickableEvents,
            cells: gnssFilters.filtered,
            updatedAt: gnss.updated_at,
            interference,
            onSelect: choose,
            onClose: close,
          }}
        />
      )}
    </div>
  );
}
