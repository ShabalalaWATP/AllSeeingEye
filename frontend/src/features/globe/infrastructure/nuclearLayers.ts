import { IconLayer, ScatterplotLayer } from '@deck.gl/layers';
import type { Layer, PickingInfo } from '@deck.gl/core';
import type { NuclearFacility } from '@/lib/api/infrastructure';
import type { InfrastructureSelection } from './useInfrastructure';
import { SYMBOL_WINDING } from '@/lib/map/symbolWinding';

const RADIATION = `data:image/svg+xml;utf8,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><g fill="white"><circle cx="32" cy="32" r="5"/><path d="M24 26 9 17A27 27 0 0 1 55 17L40 26A10 10 0 0 0 24 26ZM41 32h17A27 27 0 0 1 35 59V41A10 10 0 0 0 41 32ZM28 41v18A27 27 0 0 1 6 32h17A10 10 0 0 0 28 41Z"/></g></svg>')}`;
export function nuclearLayers(
  items: NuclearFacility[],
  selected: InfrastructureSelection | null,
  choose: (value: InfrastructureSelection) => void,
  globe: boolean,
): Layer[] {
  const selectedId = selected?.kind === 'nuclear' ? selected.item.id : null;
  const layers: Layer[] = [
    new IconLayer<NuclearFacility>({
      id: 'nuclear-facilities',
      data: items,
      pickable: true,
      billboard: !globe,
      parameters: SYMBOL_WINDING,
      getPosition: (item) => [item.longitude, item.latitude],
      getIcon: () => ({ url: RADIATION, width: 64, height: 64, mask: true }),
      getSize: (item) => (item.id === selectedId ? 32 : 24),
      sizeUnits: 'pixels',
      getColor: [251, 191, 36, 245],
      getAngle: globe ? 180 : 0,
      updateTriggers: { getSize: [selectedId] },
      onClick: (info: PickingInfo<NuclearFacility>) => {
        if (info.object) choose({ kind: 'nuclear', item: info.object });
        return true;
      },
    }),
  ];
  if (selected?.kind === 'nuclear')
    layers.push(
      new ScatterplotLayer<NuclearFacility>({
        id: 'selected-nuclear-facility-halo',
        data: [selected.item],
        pickable: false,
        filled: false,
        stroked: true,
        radiusUnits: 'pixels',
        lineWidthUnits: 'pixels',
        getRadius: 23,
        getLineWidth: 3,
        getLineColor: [255, 255, 255, 255],
        getPosition: (item) => [item.longitude, item.latitude],
      }),
    );
  return layers;
}
