import { IconLayer, ScatterplotLayer } from '@deck.gl/layers';
import type { Layer, PickingInfo } from '@deck.gl/core';
import type { DataCentre } from '@/lib/api/infrastructure';
import type { InfrastructureSelection } from './useInfrastructure';
import { SYMBOL_WINDING } from '@/lib/map/symbolWinding';

const RACK = `data:image/svg+xml;utf8,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><g fill="none" stroke="white" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"><rect x="12" y="8" width="40" height="48" rx="4"/><path d="M12 24h40M12 40h40M20 16h2M20 32h2M20 48h2M30 16h14M30 32h14M30 48h14"/></g></svg>')}`;

export function dataCentreLayers(
  items: DataCentre[],
  selected: InfrastructureSelection | null,
  choose: (value: InfrastructureSelection) => void,
  globe: boolean,
): Layer[] {
  const selectedId = selected?.kind === 'data_centre' ? selected.item.id : null;
  const layers: Layer[] = [
    new IconLayer<DataCentre>({
      id: 'data-centres',
      data: items,
      pickable: true,
      billboard: !globe,
      parameters: SYMBOL_WINDING,
      getPosition: (item) => [item.longitude, item.latitude],
      getIcon: () => ({ url: RACK, width: 64, height: 64, mask: true }),
      getSize: (item) => (item.id === selectedId ? 28 : 18),
      sizeUnits: 'pixels',
      getColor: [196, 181, 253, 235],
      getAngle: globe ? 180 : 0,
      updateTriggers: { getSize: [selectedId] },
      onClick: (info: PickingInfo<DataCentre>) => {
        if (info.object) choose({ kind: 'data_centre', item: info.object });
        return true;
      },
    }),
  ];
  if (selected?.kind === 'data_centre')
    layers.push(
      new ScatterplotLayer<DataCentre>({
        id: 'selected-data-centre-halo',
        data: [selected.item],
        pickable: false,
        filled: false,
        stroked: true,
        radiusUnits: 'pixels',
        lineWidthUnits: 'pixels',
        getRadius: 20,
        getLineWidth: 3,
        getLineColor: [255, 255, 255, 255],
        getPosition: (item) => [item.longitude, item.latitude],
      }),
    );
  return layers;
}
