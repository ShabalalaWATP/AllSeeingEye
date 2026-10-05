import type { ReactNode } from 'react';
import { GlobeInspectors } from './GlobeInspectors';
import { GlobePageControls } from './GlobePageControls';
import { LiveViewNotice } from './LiveViewNotice';
import { MaritimeAttribution } from './MaritimeAttribution';
import type { MapPanel } from './mapToolDefinitions';
import { useGlobeEventScope } from './GlobeEventScope';
import type { GlobePanelRoute } from './useGlobePanelRoute';

/** Live consumers share one scope; shell-owned elements retain their own subscriptions. */
export function GlobeEventViews({
  route,
  stylePanel,
  readouts,
}: {
  route: GlobePanelRoute;
  stylePanel: MapPanel;
  readouts: ReactNode;
}) {
  const page = useGlobeEventScope();
  const { display, canvas, events, sources, actions, liveViews } = page;
  const { opsRoom, interference } = display;
  const { tools } = canvas;
  const { radar, network, news, cyber, regions, infrastructure, cameras, figures, context } =
    sources;
  return (
    <>
      {!opsRoom && (
        <LiveViewNotice notice={liveViews.opening.notice} onClose={liveViews.opening.dismiss} />
      )}
      <MaritimeAttribution
        events={events.quality.filtered}
        hidden={events.hidden.includes('maritime')}
      />
      {!opsRoom && <GlobePageControls page={page} route={route} stylePanel={stylePanel} />}
      {readouts}
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
    </>
  );
}
