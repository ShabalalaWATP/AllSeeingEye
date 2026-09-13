import { IconLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers';
import type { Layer, PickingInfo } from '@deck.gl/core';
import { CYBER_SHIELD_ICON } from '@/lib/cyber';
import { SYMBOL_WINDING } from '@/lib/map/symbolWinding';
import type { CyberCountryContext } from '../cyberCountryContext';

/** Explicit country reference markers, never attack endpoints, incident pins or paths. */
export function cyberCountryLayers(
  groups: readonly CyberCountryContext[],
  selected: CyberCountryContext | null,
  onSelect: (group: CyberCountryContext) => void,
  flat: boolean,
  pickable = true,
): Layer[] {
  if (!groups.length) return [];
  const onClick = ({ object }: PickingInfo<CyberCountryContext>) => {
    if (object) onSelect(object);
    return true;
  };
  return [
    new ScatterplotLayer<CyberCountryContext>({
      id: 'cyber-country-context-badges',
      data: groups,
      getPosition: (item) => item.country.centroid,
      radiusUnits: 'pixels',
      getRadius: 19,
      filled: true,
      stroked: true,
      getFillColor: [10, 14, 21, 235],
      getLineColor: (item) =>
        item.country.iso2 === selected?.country.iso2 ? [255, 255, 255, 255] : [34, 211, 238, 220],
      lineWidthUnits: 'pixels',
      getLineWidth: 2,
      updateTriggers: { getLineColor: [selected?.country.iso2] },
      pickable,
      onClick,
    }),
    new IconLayer<CyberCountryContext>({
      id: 'cyber-country-context-icons',
      data: groups,
      billboard: flat,
      parameters: SYMBOL_WINDING,
      getAngle: flat ? 0 : 180,
      getPosition: (item) => item.country.centroid,
      getIcon: () => ({ url: CYBER_SHIELD_ICON, width: 64, height: 64, mask: true }),
      getColor: [34, 211, 238, 240],
      getSize: 26,
      sizeUnits: 'pixels',
      pickable,
      onClick,
    }),
    new TextLayer<CyberCountryContext>({
      id: 'cyber-country-context-labels',
      data: groups,
      billboard: flat,
      parameters: SYMBOL_WINDING,
      getAngle: flat ? 0 : 180,
      getPosition: (item) => item.country.centroid,
      getText: (item) => `${item.country.iso2} · ${item.events.length}\nCYBER COUNTRY CONTEXT`,
      characterSet: 'auto',
      getSize: 10,
      getColor: [160, 234, 244, 255],
      getPixelOffset: [0, 35],
      background: true,
      getBackgroundColor: [7, 10, 14, 230],
      getTextAnchor: 'middle',
      pickable: false,
    }),
  ];
}
