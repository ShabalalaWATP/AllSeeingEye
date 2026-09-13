import { IconLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers';
import type { Layer, PickingInfo } from '@deck.gl/core';
import { SYMBOL_WINDING } from '@/lib/map/symbolWinding';
import type { NetworkCountryGroup } from '../networkContext';

const NETWORK_PATH = 'M9 3h6v6H9V3ZM2 16h6v6H2v-6Zm14 0h6v6h-6v-6ZM12 9v4M5 16v-3h14v3';
const NETWORK_ICON = `data:image/svg+xml;utf8,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24"><path d="${NETWORK_PATH}" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`)}`;

/** Country-centroid badges are references to attribution, never inferred outage positions. */
export function networkCountryLayers(
  groups: readonly NetworkCountryGroup[],
  selected: NetworkCountryGroup | null,
  onSelect: (group: NetworkCountryGroup) => void,
  flat: boolean,
  pickable = true,
): Layer[] {
  if (!groups.length) return [];
  const onClick = ({ object }: PickingInfo<NetworkCountryGroup>) => {
    if (object) onSelect(object);
    return true;
  };
  return [
    new ScatterplotLayer<NetworkCountryGroup>({
      id: 'network-country-badges',
      data: groups,
      getPosition: (item) => item.country.centroid,
      radiusUnits: 'pixels',
      getRadius: (item) => (item.country.iso2 === selected?.country.iso2 ? 22 : 18),
      filled: true,
      stroked: true,
      getFillColor: [10, 14, 21, 235],
      getLineColor: (item) =>
        item.country.iso2 === selected?.country.iso2 ? [255, 255, 255, 255] : [251, 191, 36, 230],
      lineWidthUnits: 'pixels',
      getLineWidth: 2,
      updateTriggers: {
        getRadius: [selected?.country.iso2],
        getLineColor: [selected?.country.iso2],
      },
      pickable,
      onClick,
    }),
    new IconLayer<NetworkCountryGroup>({
      id: 'network-country-icons',
      data: groups,
      billboard: flat,
      parameters: SYMBOL_WINDING,
      getAngle: flat ? 0 : 180,
      getPosition: (item) => item.country.centroid,
      getIcon: () => ({ url: NETWORK_ICON, width: 64, height: 64, mask: true }),
      getColor: [251, 191, 36, 255],
      getSize: 26,
      sizeUnits: 'pixels',
      pickable,
      onClick,
    }),
    new TextLayer<NetworkCountryGroup>({
      id: 'network-country-labels',
      data: groups,
      billboard: flat,
      parameters: SYMBOL_WINDING,
      getAngle: flat ? 0 : 180,
      getPosition: (item) => item.country.centroid,
      getText: (item) => `${item.country.iso2} · ${item.events.length}\nNETWORK SIGNALS`,
      characterSet: 'auto',
      getSize: 10,
      getColor: [253, 230, 170, 255],
      getPixelOffset: [0, 35],
      background: true,
      getBackgroundColor: [7, 10, 14, 230],
      getTextAnchor: 'middle',
      pickable: false,
    }),
  ];
}
