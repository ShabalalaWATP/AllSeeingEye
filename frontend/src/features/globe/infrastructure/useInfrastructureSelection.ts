import { useCallback, useMemo } from 'react';
import type { ViewMode } from '@/stores/globe';
import type { GlobeEngineHandle } from '../useGlobeEngine';
import { buildInfrastructureLayers } from './infrastructureLayers';
import type { InfrastructureSelection, InfrastructureState } from './useInfrastructure';

export function useInfrastructureSelection(
  state: InfrastructureState,
  picking: boolean,
  closeOther: () => void,
  engine: GlobeEngineHandle,
  mode: ViewMode,
) {
  const select = state.select;
  const choose = useCallback(
    (value: InfrastructureSelection) => {
      if (picking) return;
      closeOther();
      select(value);
    },
    [picking, closeOther, select],
  );
  const focus = useCallback(
    (value: InfrastructureSelection) => {
      if (picking) return;
      choose(value);
      const point: [number, number] | undefined =
        value.kind === 'station' ? [value.item.longitude, value.item.latitude] : value.item.path[0];
      if (point)
        engine.flyTo({ center: [point[0], point[1]], zoom: value.kind === 'station' ? 8 : 4 });
    },
    [choose, engine, picking],
  );
  const { data, cablesEnabled, stationsEnabled, selected } = state;
  const layers = useMemo(
    () =>
      buildInfrastructureLayers(
        { data, cablesEnabled, stationsEnabled, selected },
        choose,
        mode === 'globe',
      ),
    [data, cablesEnabled, stationsEnabled, selected, choose, mode],
  );
  return { layers, focus };
}
