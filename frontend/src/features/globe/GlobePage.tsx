/** Full-canvas globe with on-demand layer and measurement tools. */
import { SavedMapAreaNotice } from './SavedMapAreaNotice';
import { GlobeInspectors } from './GlobeInspectors';
import { MapCanvas } from './MapCanvas';
import { MaritimeAttribution } from './MaritimeAttribution';
import { MapStatusReadouts } from './MapStatusReadouts';
import { GlobeHeading } from './GlobeHeading';
import { GlobePageControls } from './GlobePageControls';
import { ModeToolbar } from './ModeToolbar';
import { useGlobePage } from './useGlobePage';
import { useGlobePanelRoute } from './useGlobePanelRoute';
import { LiveViewNotice } from './LiveViewNotice';
import './dashboard.css';

export { FOCUS_ZOOM } from './useMapFocus';
export default function GlobePage() {
  const page = useGlobePage();
  const route = useGlobePanelRoute();
  const { display, canvas, events, sources, actions, liveViews } = page;
  const { mode, opsRoom, interference } = display;
  const { containerRef, supported, engine, britishGrid, tools, savedArea } = canvas;
  const { radar, network, news, cyber, regions, infrastructure, cameras, figures, context } =
    sources;
  return (
    <div className="globe-dashboard absolute inset-0 bg-ground">
      <GlobeHeading mode={mode} showRef={opsRoom ? null : route.showPanel} />
      <MapCanvas containerRef={containerRef} supported={supported} mode={mode} engine={engine} />
      {!opsRoom && <ModeToolbar mode={mode} onChange={display.setMode} />}
      {!opsRoom && <SavedMapAreaNotice area={savedArea} />}
      {!opsRoom && (
        <LiveViewNotice notice={liveViews.opening.notice} onClose={liveViews.opening.dismiss} />
      )}
      <MaritimeAttribution
        events={events.quality.filtered}
        hidden={events.hidden.includes('maritime')}
      />
      {!opsRoom && <GlobePageControls page={page} route={route} />}
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
          news={{ state: news, onSelect: actions.selectContext }}
          cyber={{ state: cyber, onSelect: actions.cyberSelection.selectRecord }}
          regions={regions}
          infrastructure={infrastructure}
          cameras={cameras}
          figures={figures}
          eventDetails={{
            selected: events.selected ?? context.event,
            storySize: events.storySize,
            details: events.details,
            events: events.pickableEvents,
            cells: sources.gnssFilters.filtered,
            updatedAt: sources.gnss.updated_at,
            interference,
            onSelect: events.choose,
            onClose: events.close,
          }}
        />
      )}
    </div>
  );
}
