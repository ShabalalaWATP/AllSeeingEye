/** The map surface: one guarded engine with its viewport, tools, reference data and saved area. */
import { useMemo } from 'react';
import type { useGlobePreferences } from './useGlobePreferences';
import { useDashboardEngine } from './useDashboardEngine';
import { useBritishGrid } from './useBritishGrid';
import { useViewportCoverage } from './useViewportCoverage';
import { useMapWorkspaceTools } from './useMapWorkspaceTools';
import { useMapRenderView } from './useMapRenderView';
import { useMapReferenceData } from './useMapReferenceData';
import { useSavedMapArea } from './useSavedMapArea';

export type GlobeDisplay = ReturnType<typeof useGlobePreferences>;

/**
 * Engine creation depends only on its mount inputs, so panel, selection and event changes
 * re-render this hook without recreating the map or its listeners.
 */
export function useGlobeCanvas(
  { mode, baseLayer, setBaseLayer, lite, opsRoom }: GlobeDisplay,
  visible: boolean,
) {
  const { supported, containerRef, engine } = useDashboardEngine({ mode, baseLayer, lite });
  const britishGrid = useBritishGrid(engine);
  useViewportCoverage(engine, supported && visible);
  const tools = useMapWorkspaceTools(engine, supported && !opsRoom, mode);
  const { zoom, symbolMode } = useMapRenderView(engine, mode);
  const reference = useMapReferenceData(baseLayer, setBaseLayer);
  const savedArea = useSavedMapArea(engine, reference.countryByIso, mode === 'map');
  // Workspace tools draw beneath a saved area outline, above every catalogue.
  const toolLayers = useMemo(
    () => [...tools.layers, ...savedArea.layers],
    [tools.layers, savedArea.layers],
  );
  return {
    supported,
    containerRef,
    engine,
    britishGrid,
    tools,
    savedArea,
    toolLayers,
    zoom,
    symbolMode,
    reference,
  };
}

export type GlobeCanvas = ReturnType<typeof useGlobeCanvas>;
