/** Full-canvas globe with on-demand layer and measurement tools. */
import { SavedMapAreaNotice } from './SavedMapAreaNotice';
import { usePageVisible, useReducedMotion } from '@/components/brand/useMotionPreferences';
import { MapCanvas } from './MapCanvas';
import { MapStatusReadouts } from './MapStatusReadouts';
import { GlobeHeading } from './GlobeHeading';
import { ModeToolbar } from './ModeToolbar';
import { GlobeEventScope } from './GlobeEventScope';
import { GlobeEventViews } from './GlobeEventViews';
import { mapStylePanel } from './MapReferencePanels';
import { useGlobeCanvas } from './useGlobeCanvas';
import { useGlobePreferences } from './useGlobePreferences';
import { useGlobePanelRoute } from './useGlobePanelRoute';
import './dashboard.css';
import { basemapUnavailable, useMapSourcePolicy } from '@/lib/map/sourcePolicy';

export { FOCUS_ZOOM } from './useMapFocus';
export default function GlobePage() {
  const display = useGlobePreferences();
  const policy = useMapSourcePolicy();
  const policyReason = basemapUnavailable(policy, display.baseLayer);
  const visible = usePageVisible();
  const reducedMotion = useReducedMotion();
  const canvas = useGlobeCanvas(display, visible);
  const route = useGlobePanelRoute();
  const { mode, opsRoom } = display;
  const { containerRef, supported, engine, britishGrid, tools, savedArea, reference } = canvas;
  const stylePanel = mapStylePanel({
    display: {
      terminator: display.terminator,
      lite: display.lite,
      onToggleTerminator: display.toggleTerminator,
      onToggleLite: display.toggleLite,
    },
    base: {
      initialExpanded: true,
      value: display.baseLayer,
      osAvailable: reference.osMaps,
      osChecking: reference.osLoading,
      osError: reference.osError,
      onCheckOs: reference.recheckOs,
      onChange: display.setBaseLayer,
    },
  });
  return (
    <GlobeEventScope
      display={display}
      canvas={canvas}
      visible={visible}
      reducedMotion={reducedMotion}
    >
      <div className="globe-dashboard absolute inset-0 bg-ground">
        <GlobeHeading mode={mode} showRef={opsRoom ? null : route.showPanel} />
        <MapCanvas containerRef={containerRef} supported={supported} mode={mode} engine={engine} />
        {policyReason && <p role="status" className="absolute top-20 left-3 z-10 max-w-sm rounded bg-surface p-3 text-xs">{policyReason}. Choose an available basemap in map style settings.</p>}
        {!opsRoom && <ModeToolbar mode={mode} onChange={display.setMode} />}
        {!opsRoom && <SavedMapAreaNotice area={savedArea} />}
        <GlobeEventViews
          route={route}
          stylePanel={stylePanel}
          readouts={
            <MapStatusReadouts
              tools={tools}
              engine={engine}
              supported={supported}
              opsRoom={opsRoom}
              bng={britishGrid.enabled}
            />
          }
        />
      </div>
    </GlobeEventScope>
  );
}
