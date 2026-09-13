import { IconLayer, ScatterplotLayer } from '@deck.gl/layers';
import type { Layer, PickingInfo } from '@deck.gl/core';
import type { Site } from '@/lib/api/infrastructure';
import type { InfrastructureSelection } from './useInfrastructure';
import { SYMBOL_WINDING } from '@/lib/map/symbolWinding';

const svg = (body: string) =>
  `data:image/svg+xml;utf8,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><g fill="none" stroke="white" stroke-width="5" stroke-linecap="round" stroke-linejoin="round">${body}</g></svg>`)}`;
// A derrick for oil and gas, a wafer for semiconductors.
const DERRICK = svg('<path d="M22 58 32 8l10 50M12 58h40M26 40h12M28 26h8M18 58l14-14 14 14"/>');
const WAFER = svg(
  '<circle cx="32" cy="32" r="24"/><path d="M14 22h36M14 42h36M22 12v40M42 12v40M32 8v48"/>',
);
const COLOURS: Record<'energy' | 'semiconductor', [number, number, number, number]> = {
  energy: [255, 170, 90, 240],
  semiconductor: [130, 210, 255, 240],
};

export function siteLayers(
  category: 'energy' | 'semiconductor',
  items: Site[],
  selected: InfrastructureSelection | null,
  choose: (value: InfrastructureSelection) => void,
  globe: boolean,
): Layer[] {
  const kind = category === 'energy' ? 'energy_site' : 'semiconductor_site';
  const selectedId = selected?.kind === kind ? selected.item.id : null;
  const layers: Layer[] = [
    new IconLayer<Site>({
      id: `${category}-sites`,
      data: items,
      pickable: true,
      billboard: !globe,
      parameters: SYMBOL_WINDING,
      getPosition: (item) => [item.longitude, item.latitude],
      getIcon: () => ({
        url: category === 'energy' ? DERRICK : WAFER,
        width: 64,
        height: 64,
        mask: true,
      }),
      getSize: (item) => (item.id === selectedId ? 30 : item.significance ? 24 : 18),
      sizeUnits: 'pixels',
      getColor: COLOURS[category],
      getAngle: globe ? 180 : 0,
      updateTriggers: { getSize: [selectedId] },
      onClick: (info: PickingInfo<Site>) => {
        if (info.object) choose({ kind, item: info.object });
        return true;
      },
    }),
  ];
  if (selected?.kind === kind)
    layers.push(
      new ScatterplotLayer<Site>({
        id: `selected-${category}-site-halo`,
        data: [selected.item],
        pickable: false,
        filled: false,
        stroked: true,
        radiusUnits: 'pixels',
        lineWidthUnits: 'pixels',
        getRadius: 22,
        getLineWidth: 3,
        getLineColor: [255, 255, 255, 255],
        getPosition: (item) => [item.longitude, item.latitude],
      }),
    );
  return layers;
}
