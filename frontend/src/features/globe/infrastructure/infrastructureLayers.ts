import { IconLayer, PathLayer, ScatterplotLayer } from '@deck.gl/layers';
import type { Layer, PickingInfo } from '@deck.gl/core';
import type { Cable, GroundStation } from '@/lib/api/infrastructure';
import { nuclearLayers } from './nuclearLayers';
import type { InfrastructureSelection, InfrastructureState } from './useInfrastructure';
import { SYMBOL_WINDING } from '@/lib/map/symbolWinding';

const DISH = `data:image/svg+xml;utf8,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><g fill="none" stroke="white" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 13a28 28 0 0 0 39 39L12 13ZM32 35 45 22M26 48l-5 12h30M42 8a17 17 0 0 1 14 14M42 18a7 7 0 0 1 4 4"/></g></svg>')}`;

export function buildInfrastructureLayers(
  state: Pick<InfrastructureState, 'data' | 'cablesEnabled' | 'stationsEnabled' | 'selected'> & {
    nuclearEnabled?: boolean;
  },
  onSelect: (selection: InfrastructureSelection) => void,
  globe = false,
): Layer[] {
  if (!state.data) return [];
  const layers: Layer[] = [];
  if (state.cablesEnabled)
    layers.push(
      new PathLayer<Cable>({
        id: 'undersea-cables',
        data: state.data.cables,
        pickable: true,
        wrapLongitude: true,
        getPath: (item) => item.path,
        getColor: (item) =>
          item.id === state.selected?.item.id && state.selected.kind === 'cable'
            ? [255, 255, 255, 255]
            : [111, 184, 209, 170],
        getWidth: (item) =>
          item.id === state.selected?.item.id && state.selected.kind === 'cable' ? 5 : 2,
        widthUnits: 'pixels',
        widthMinPixels: 2,
        capRounded: true,
        jointRounded: true,
        updateTriggers: {
          getColor: [state.selected?.item.id],
          getWidth: [state.selected?.item.id],
        },
        onClick: (info: PickingInfo<Cable>) => {
          if (info.object) onSelect({ kind: 'cable', item: info.object });
          return true;
        },
      }),
    );
  if (state.stationsEnabled) {
    layers.push(
      new IconLayer<GroundStation>({
        id: 'satellite-ground-stations',
        data: state.data.ground_stations,
        pickable: true,
        billboard: !globe,
        parameters: SYMBOL_WINDING,
        getPosition: (station) => [station.longitude, station.latitude],
        getIcon: () => ({ url: DISH, width: 64, height: 64, mask: true }),
        getSize: (station) => (station.id === state.selected?.item.id ? 32 : 24),
        sizeUnits: 'pixels',
        getColor: [125, 218, 236, 245],
        getAngle: globe ? 180 : 0,
        updateTriggers: { getSize: [state.selected?.item.id] },
        onClick: (info: PickingInfo<GroundStation>) => {
          if (info.object) onSelect({ kind: 'station', item: info.object });
          return true;
        },
      }),
    );
    if (state.selected?.kind === 'station')
      layers.push(
        new ScatterplotLayer<GroundStation>({
          id: 'selected-ground-station-halo',
          data: [state.selected.item],
          pickable: false,
          filled: false,
          stroked: true,
          radiusUnits: 'pixels',
          lineWidthUnits: 'pixels',
          getRadius: 23,
          getLineWidth: 3,
          getLineColor: [255, 255, 255, 255],
          getPosition: (station) => [station.longitude, station.latitude],
        }),
      );
  }
  if (state.nuclearEnabled)
    layers.push(...nuclearLayers(state.data.nuclear_facilities, state.selected, onSelect, globe));
  return layers;
}
