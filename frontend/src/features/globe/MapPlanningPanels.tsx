import { MapMeasurementPanel } from '@/components/maps/MapMeasurementPanel';
import { MapAreaResearchPanel } from '@/components/maps/MapAreaResearchPanel';
import { RfCalculatorPanel } from '@/components/maps/RfCalculatorPanel';
import { RoutePlannerPanel } from '@/components/maps/RoutePlannerPanel';
import { TerrainAnalysisPanel } from '@/components/maps/TerrainAnalysisPanel';
import { CoordinateWorkbench } from '@/components/maps/CoordinateWorkbench';
import { CorridorResearchPanel } from '@/components/maps/CorridorResearchPanel';
import { NuclearEducationPanel } from '@/components/maps/NuclearEducationPanel';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { Position } from '@/lib/map/geoJsonTypes';
import { researchAreaGeometry } from '@/lib/map/researchAreaGeometry';
import { measure } from '@/lib/map/measurements';
import { ControlPanel, type OpenPanel } from './GlobeControls';
import { MapWorkspacePanel } from './MapWorkspacePanel';
import { MapDrawingPanel } from './MapDrawingPanel';
import { MapResearchDrawingControls } from './MapResearchDrawingControls';
import type { useMapWorkspaceTools } from './useMapWorkspaceTools';

/** Direct panel children allow the shared rail to manage one active tool. */
export function mapPlanningPanels(
  tools: ReturnType<typeof useMapWorkspaceTools>,
  {
    open = () => undefined,
    events = [],
    onHighlight = () => undefined,
    onNavigate = () => undefined,
  }: {
    open?: OpenPanel;
    events?: readonly LiveEvent[];
    onHighlight?: (event: LiveEvent) => void;
    onNavigate?: (position: Position) => void;
  } = {},
) {
  const { measurement } = tools;
  const selectedPoints =
    tools.drawingWorkspace.selected?.anchors ??
    (tools.drawing.points.length ? tools.drawing.points : measurement.points);
  const corridorPoints =
    tools.drawingWorkspace.selected?.shape === 'path'
      ? tools.drawingWorkspace.selected.anchors
      : tools.drawing.shape === 'path' && tools.drawing.points.length > 1
        ? tools.drawing.points
        : (tools.routePlanner.route?.coordinates ??
          (measurement.mode === 'distance' ? measurement.points : []));
  return [
    <ControlPanel key="workspace" label="On this map" icon="layers" size="medium">
      <MapWorkspacePanel tools={tools} open={open} />
    </ControlPanel>,
    <ControlPanel key="research" side="right" label="Research area" icon="research" size="medium">
      <MapAreaResearchPanel
        area={tools.research.area}
        areaError={tools.research.areaError}
        picking={tools.research.drawing.picking}
        onStopDrawing={() => tools.research.drawing.setPicking(false)}
        events={events}
        onHighlight={onHighlight}
      >
        {tools.research.imported ? (
          <div className="map-tool-section">
            <p className="map-tool-help">
              Using the selected boundary. Research keeps its exact geometry.
            </p>
            <button type="button" className="map-tool-secondary" onClick={tools.research.clear}>
              Clear boundary and draw another
            </button>
          </div>
        ) : (
          <MapResearchDrawingControls value={tools.research.drawing} />
        )}
      </MapAreaResearchPanel>
    </ControlPanel>,
    <ControlPanel
      key="drawing"
      side="right"
      label="Draw on map"
      caption="Draw"
      icon="draw"
      size="medium"
    >
      <MapDrawingPanel
        value={tools.drawing}
        workspace={tools.drawingWorkspace}
        onResearch={(shape, anchors) => {
          tools.adoptResearch(researchAreaGeometry(shape, anchors));
          open('Research area');
        }}
        onRadioSite={(point) => {
          tools.rf.setSite('origin', point);
          open('RF link calculator');
        }}
      />
    </ControlPanel>,
    <ControlPanel key="route" side="right" label="Route planner" icon="route" size="medium">
      <RoutePlannerPanel
        onRouteChange={tools.setRoute}
        draft={tools.routePlanner.draft}
        onDraftChange={tools.routePlanner.setDraft}
        result={tools.routePlanner.route}
        {...(measurement.points.length >= 2
          ? { initialWaypoints: measurement.points.slice(0, 8).map(([lon, lat]) => ({ lon, lat })) }
          : {})}
      />
      <CorridorResearchPanel
        points={corridorPoints}
        onResearchArea={(area) => {
          tools.adoptResearch(area);
          open('Research area');
        }}
      />
    </ControlPanel>,
    <ControlPanel
      key="rf"
      side="right"
      label="RF link calculator"
      title="Radio planning"
      caption="RF"
      icon="rf"
      size="medium"
    >
      <RfCalculatorPanel
        siteNames={tools.rf.siteNames}
        onSetSite={tools.rf.setSite}
        onSwapSites={tools.rf.swapSites}
        interaction={tools.rf.interaction}
        {...(tools.rf.canDrag ? { onDragSite: tools.rf.setDragSite } : {})}
        studyWorkspace={tools.rf}
        onProfilePoint={tools.rf.setProfilePoint}
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
    <ControlPanel
      key="measure"
      label="Measure distance and area"
      caption="Measure"
      icon="measure"
      size="medium"
    >
      <MapMeasurementPanel key={measurement.resetSequence} value={measurement} />
    </ControlPanel>,
    <ControlPanel key="terrain" label="Terrain profile and visibility" icon="measure" size="medium">
      <TerrainAnalysisPanel points={selectedPoints} study={tools.terrainStudy} />
    </ControlPanel>,
    <ControlPanel key="coordinates" label="Coordinates" icon="grid" size="medium">
      <CoordinateWorkbench onNavigate={onNavigate} />
    </ControlPanel>,
    <ControlPanel
      key="nuclear-education"
      label="Nuclear effects (education)"
      icon="guide"
      size="medium"
    >
      <NuclearEducationPanel />
    </ControlPanel>,
  ];
}
