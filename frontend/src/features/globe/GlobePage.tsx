/** Full-canvas globe with on-demand layer and measurement tools. */
import { useRef } from 'react';
import { useLocation, useSearchParams } from 'react-router';

import { mapPanelId, readMapPanel } from '@/lib/mapLayerDirectory';

import { SavedMapAreaNotice } from './SavedMapAreaNotice';
import { GlobeInspectors } from './GlobeInspectors';
import { MapCanvas } from './MapCanvas';
import { MaritimeAttribution } from './MaritimeAttribution';
import { dashboardCataloguePanels } from './dashboardCataloguePanels';
import { eventControlPanels } from './eventControlPanels';
import { MapStatusReadouts } from './MapStatusReadouts';
import { MapToolActivity } from './MapToolActivity';
import { GlobeControls, type ShowPanel } from './GlobeControls';
import { GlobeHeading } from './GlobeHeading';
import { DashboardLayerRail } from './DashboardLayerRail';
import { MapNavigationTools } from './MapNavigationTools';
import { ModeToolbar } from './ModeToolbar';
import { mapPlanningPanels } from './MapPlanningPanels';
import { mapReferencePanels } from './MapReferencePanels';
import { mapGuidePanel } from './MapGuidePanel';
import { useGlobePage } from './useGlobePage';
import { LiveViewNotice } from './LiveViewNotice';
import { liveViewPanels } from './liveViewPanels';
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
    liveViews,
    now,
  } = useGlobePage();
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const requestedPanel = readMapPanel(params);
  const showPanel = useRef<ShowPanel | null>(null);
  return (
    <div className="globe-dashboard absolute inset-0 bg-ground">
      <GlobeHeading mode={mode} showRef={opsRoom ? null : showPanel} />
      <MapCanvas containerRef={containerRef} supported={supported} mode={mode} engine={engine} />
      {!opsRoom && <ModeToolbar mode={mode} onChange={setMode} />}
      {!opsRoom && <SavedMapAreaNotice area={savedArea} />}
      {!opsRoom && (
        <LiveViewNotice notice={liveViews.opening.notice} onClose={liveViews.opening.dismiss} />
      )}
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
          activity={<MapToolActivity tools={tools} />}
          requestedPanel={requestedPanel}
          requestKey={location.key}
          showRef={showPanel}
          onPanelChange={(label) => {
            const next = new URLSearchParams(params);
            if (label) next.set('panel', mapPanelId(label) ?? label);
            else next.delete('panel');
            if (next.toString() !== params.toString()) setParams(next);
          }}
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
            mapPlanningPanels(tools, {
              open: openPanel,
              events: data.list,
              onHighlight: focus,
              onNavigate: (center) => engine.flyTo({ center, zoom: 12 }),
            }),
            eventControlPanels(data, networkSelection.selectRecord),
            liveViewPanels(liveViews),
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
