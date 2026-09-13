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
        value.kind === 'cable'
          ? value.item.path[0]
          : value.kind === 'military_country'
            ? value.item.country.centroid
            : [value.item.longitude, value.item.latitude];
      if (point)
        engine.flyTo({
          center: [point[0], point[1]],
          zoom: value.kind === 'military_country' ? 3 : value.kind === 'cable' ? 4 : 8,
        });
    },
    [choose, engine, picking],
  );
  const {
    data,
    cablesEnabled,
    stationsEnabled,
    nuclearEnabled,
    dataCentresEnabled,
    energyEnabled,
    semiconductorEnabled,
    militaryEnabled,
    militaryCountries,
    selected,
  } = state;
  const layers = useMemo(
    () =>
      buildInfrastructureLayers(
        {
          data,
          cablesEnabled,
          stationsEnabled,
          nuclearEnabled,
          dataCentresEnabled,
          energyEnabled,
          semiconductorEnabled,
          militaryEnabled,
          militaryCountries,
          selected,
        },
        choose,
        mode === 'globe',
      ),
    [
      data,
      cablesEnabled,
      stationsEnabled,
      nuclearEnabled,
      dataCentresEnabled,
      energyEnabled,
      semiconductorEnabled,
      militaryEnabled,
      militaryCountries,
      selected,
      choose,
      mode,
    ],
  );
  return { layers, focus };
}
