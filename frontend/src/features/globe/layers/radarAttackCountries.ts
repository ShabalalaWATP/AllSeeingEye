import { TextLayer } from '@deck.gl/layers';
import type { Layer, PickingInfo } from '@deck.gl/core';
import { SYMBOL_WINDING } from '@/lib/map/symbolWinding';
import type { RadarAttackCountry } from '../radarAttackCountries';

const share = (value: number | null) => (value === null ? '—' : `${value.toFixed(1)}%`);

/** Offset pills distinguish aggregate Cloudflare distributions from cyber incident markers. */
export function radarAttackCountryLayers(
  rows: readonly RadarAttackCountry[],
  selectedIso: string | null,
  onSelect: (row: RadarAttackCountry) => void,
  flat: boolean,
  pickable = true,
): Layer[] {
  if (!rows.length) return [];
  return [
    new TextLayer<RadarAttackCountry>({
      id: 'radar-attack-country-shares',
      data: rows,
      billboard: flat,
      parameters: SYMBOL_WINDING,
      getAngle: flat ? 0 : 180,
      getPosition: (row) => row.country.centroid,
      getPixelOffset: [0, -48],
      getText: (row) =>
        `CF ${row.country.iso2} · L3/4 ${share(row.layer3)} · L7 ${share(row.layer7)}`,
      getSize: 11,
      getColor: [250, 245, 255, 255],
      getBackgroundColor: (row) =>
        row.country.iso2 === selectedIso ? [107, 33, 168, 255] : [49, 23, 79, 245],
      background: true,
      backgroundPadding: [7, 5],
      getBorderColor: [216, 180, 254, 245],
      getBorderWidth: 1,
      getTextAnchor: 'middle',
      pickable,
      onClick: ({ object }: PickingInfo<RadarAttackCountry>) => {
        if (object) onSelect(object);
        return true;
      },
      updateTriggers: { getBackgroundColor: [selectedIso] },
    }),
  ];
}
