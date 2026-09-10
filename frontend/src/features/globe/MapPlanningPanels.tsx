import { MapMeasurementPanel } from '@/components/maps/MapMeasurementPanel';
import { RfCalculatorPanel } from '@/components/maps/RfCalculatorPanel';
import { RoutePlannerPanel } from '@/components/maps/RoutePlannerPanel';
import { measure } from '@/lib/map/measurements';
import { ControlPanel } from './GlobeControls';
import { MapDrawingPanel } from './MapDrawingPanel';
import type { useMapWorkspaceTools } from './useMapWorkspaceTools';

/** Direct panel children allow the shared rail to manage one active tool. */
export function mapPlanningPanels(tools: ReturnType<typeof useMapWorkspaceTools>) {
  const { measurement } = tools;
  return [
    <ControlPanel key="drawing" side="right" label="Draw on map" caption="Draw" icon="draw">
      <MapDrawingPanel value={tools.drawing} />
    </ControlPanel>,
    <ControlPanel key="route" side="right" label="Route planner" icon="route">
      <RoutePlannerPanel
        onRouteChange={tools.setRoute}
        draft={tools.routePlanner.draft}
        onDraftChange={tools.routePlanner.setDraft}
        result={tools.routePlanner.route}
        {...(measurement.points.length >= 2
          ? { initialWaypoints: measurement.points.slice(0, 8).map(([lon, lat]) => ({ lon, lat })) }
          : {})}
      />
    </ControlPanel>,
    <ControlPanel
      key="rf"
      side="right"
      label="RF link calculator"
      caption="RF"
      icon="rf"
      size="medium"
    >
      <RfCalculatorPanel
        origin={tools.rf.origin}
        receiver={tools.rf.receiver}
        picking={tools.rf.picking}
        onPick={tools.rf.setPicking}
        onOverlayChange={tools.rf.setEstimate}
        analysis={tools.rf.analysis}
        onAnalysisChange={tools.rf.setAnalysis}
        draft={tools.rf.draft}
        onDraftChange={tools.rf.setDraft}
        onClearReceiver={tools.rf.clearReceiver}
        overlayVisible={tools.rf.estimate !== null}
        coverageBubble={tools.rf.coverageBubble}
        onCoverageBubbleChange={tools.rf.setCoverageBubble}
        {...(measurement.mode === 'distance' && measurement.points.length === 2
          ? { measuredDistanceKm: measure(measurement.points, 'distance').metres / 1000 }
          : {})}
      />
    </ControlPanel>,
    <ControlPanel key="measure" label="Measure distance and area" caption="Measure" icon="measure">
      <MapMeasurementPanel key={measurement.resetSequence} value={measurement} />
    </ControlPanel>,
  ];
}
