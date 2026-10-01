/** Connects saved live views to the existing page state. */
import { useGlobeStore } from '@/stores/globe';
import type { useDashboardEvents } from './useDashboardEvents';
import type { useGnssFilters } from './useGnssFilters';
import type { useGlobePreferences } from './useGlobePreferences';
import type { GlobeEngineHandle } from './useGlobeEngine';
import { useLiveViewControls } from './useLiveViewControls';
import { useLiveViewOpening } from './useLiveViewOpening';

export function useGlobeLiveViews(
  engine: GlobeEngineHandle,
  display: ReturnType<typeof useGlobePreferences>,
  data: ReturnType<typeof useDashboardEvents>,
  gnss: ReturnType<typeof useGnssFilters>,
) {
  const toggleInterference = useGlobeStore((state) => state.toggleInterference);
  const controls = useLiveViewControls({
    engine,
    mode: display.mode,
    setMode: display.setMode,
    baseLayer: display.baseLayer,
    setBaseLayer: display.setBaseLayer,
    terminator: display.terminator,
    toggleTerminator: display.toggleTerminator,
    interference: display.interference,
    toggleInterference,
    hidden: data.hidden,
    toggleCategory: data.toggleCategory,
    windowHours: data.windowHours,
    setWindow: data.setWindow,
    country: data.country,
    setCountry: data.setCountry,
    observations: data.observations,
    fires: data.fires,
    quality: data.quality,
    gnss,
    conflicts: data.conflicts,
  });
  const opening = useLiveViewOpening(controls);
  return { controls, opening };
}
