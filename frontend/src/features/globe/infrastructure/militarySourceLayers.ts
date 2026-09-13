import { ScatterplotLayer, TextLayer } from '@deck.gl/layers';
import type { Layer, PickingInfo } from '@deck.gl/core';
import { SYMBOL_WINDING } from '@/lib/map/symbolWinding';
import type { MilitaryCountryReference } from './militarySourceReferences';

/** Country-centroid badges distinguish reference coverage from site geometry. */
export function militarySourceLayers(
  items: readonly MilitaryCountryReference[],
  selected: MilitaryCountryReference | null,
  choose: (item: MilitaryCountryReference) => void,
  globe: boolean,
): Layer[] {
  if (!items.length) return [];
  const onClick = ({ object }: PickingInfo<MilitaryCountryReference>) => {
    if (object) choose(object);
    return true;
  };
  return [
    new ScatterplotLayer<MilitaryCountryReference>({
      id: 'military-source-countries',
      data: items,
      pickable: true,
      radiusUnits: 'pixels',
      getRadius: 22,
      filled: true,
      stroked: true,
      getFillColor: [18, 24, 35, 240],
      getLineColor: (item) =>
        item.id === selected?.id ? [255, 255, 255, 255] : [167, 194, 210, 240],
      getLineWidth: (item) => (item.id === selected?.id ? 3 : 2),
      lineWidthUnits: 'pixels',
      getPosition: (item) => item.country.centroid,
      updateTriggers: { getLineColor: [selected?.id], getLineWidth: [selected?.id] },
      onClick,
    }),
    new TextLayer<MilitaryCountryReference>({
      id: 'military-source-country-labels',
      data: items,
      pickable: true,
      billboard: !globe,
      parameters: SYMBOL_WINDING,
      getAngle: globe ? 180 : 0,
      getPosition: (item) => item.country.centroid,
      getText: (item) => item.id,
      getSize: 13,
      getColor: [226, 237, 244, 255],
      getTextAnchor: 'middle',
      getAlignmentBaseline: 'center',
      onClick,
    }),
    new TextLayer<MilitaryCountryReference>({
      id: 'military-source-country-captions',
      data: items,
      pickable: false,
      billboard: !globe,
      parameters: SYMBOL_WINDING,
      getAngle: globe ? 180 : 0,
      getPosition: (item) => item.country.centroid,
      getText: () => 'SOURCE INDEX',
      getSize: 9,
      getColor: [194, 218, 230, 255],
      getPixelOffset: [0, 32],
      getTextAnchor: 'middle',
      background: true,
      getBackgroundColor: [9, 13, 20, 230],
    }),
  ];
}
