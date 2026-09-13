import { IconLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers';
import type { PickingInfo } from '@deck.gl/core';
import { NEWS_ICON } from '@/lib/newsSymbols';
import { SYMBOL_WINDING } from '@/lib/map/symbolWinding';
import type { NewsCountryContext } from '../useNewsCountryContext';

export function newsCountryLayers(
  groups: readonly NewsCountryContext[],
  selected: NewsCountryContext | null,
  onSelect: (group: NewsCountryContext) => void,
  flat: boolean,
  pickable: boolean,
) {
  if (!groups.length) return [];
  const onClick = ({ object }: PickingInfo<NewsCountryContext>) => {
    if (object) onSelect(object);
    return true;
  };
  return [
    new ScatterplotLayer<NewsCountryContext>({
      id: 'news-country-badges',
      data: groups,
      getPosition: (item) => item.country.centroid,
      radiusUnits: 'pixels',
      getRadius: 18,
      filled: true,
      stroked: true,
      getFillColor: [10, 14, 21, 235],
      lineWidthUnits: 'pixels',
      getLineWidth: 2,
      getLineColor: (item) =>
        item.country.iso2 === selected?.country.iso2 ? [255, 255, 255, 255] : [233, 228, 220, 210],
      updateTriggers: { getLineColor: [selected?.country.iso2] },
      pickable,
      onClick,
    }),
    new IconLayer<NewsCountryContext>({
      id: 'news-country-icons',
      data: groups,
      getPosition: (item) => item.country.centroid,
      billboard: flat,
      parameters: SYMBOL_WINDING,
      getAngle: flat ? 0 : 180,
      getIcon: () => ({ url: NEWS_ICON, width: 64, height: 64, mask: true }),
      getColor: [233, 228, 220, 255],
      getSize: 24,
      sizeUnits: 'pixels',
      pickable,
      onClick,
    }),
    new TextLayer<NewsCountryContext>({
      id: 'news-country-labels',
      data: groups,
      getPosition: (item) => item.country.centroid,
      billboard: flat,
      parameters: SYMBOL_WINDING,
      getAngle: flat ? 0 : 180,
      getText: (item) => `${item.country.iso2} · ${item.events.length}\nNEWS COUNTRY CONTEXT`,
      characterSet: 'auto',
      getSize: 10,
      getColor: [233, 228, 220, 255],
      getPixelOffset: [0, 33],
      background: true,
      getBackgroundColor: [7, 10, 14, 235],
      getTextAnchor: 'middle',
      pickable: false,
    }),
  ];
}
