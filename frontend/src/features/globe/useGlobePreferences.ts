import { useShallow } from 'zustand/react/shallow';
import { useGlobeStore } from '@/stores/globe';

/** Subscribe only to display preferences owned by the dashboard. */
export function useGlobePreferences() {
  return useGlobeStore(
    useShallow((state) => ({
      mode: state.mode,
      setMode: state.setMode,
      baseLayer: state.baseLayer,
      setBaseLayer: state.setBaseLayer,
      terminator: state.terminator,
      toggleTerminator: state.toggleTerminator,
      lite: state.lite,
      toggleLite: state.toggleLite,
      interference: state.interference,
      opsRoom: state.opsRoom,
    })),
  );
}
