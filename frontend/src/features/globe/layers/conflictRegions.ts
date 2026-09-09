import { IconLayer, PathLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers';
import type { Layer, PickingInfo } from '@deck.gl/core';
import type { ConflictRegion } from '../conflictRegions';
import type { Position } from '@/lib/map/geoJsonTypes';
import { CONFLICT_REGION_MARKERS } from '../conflictRegionSymbols';
import { SYMBOL_WINDING } from '@/lib/map/symbolWinding';

const colour = (region: ConflictRegion): [number, number, number, number] =>
  region.card.conflict.status === 'war' ? [255, 106, 106, 245] : [249, 190, 84, 245];

/** Fixed regional locator symbols. Their centres are not incident coordinates or frontlines. */
export function conflictRegionLayers(
  regions: readonly ConflictRegion[],
  selected: ConflictRegion | null,
  onSelect: (region: ConflictRegion) => void,
  flat: boolean,
  pickable = true,
): Layer[] {
  if (!regions.length) return [];
  const selectedData = selected ? [selected] : [];
  const selectRegion = ({ object }: PickingInfo<ConflictRegion>) => {
    if (object) onSelect(object);
    return true;
  };
  const outline: Position[][] = selected
    ? (() => {
        const [w, s, e, n] = selected.bounds;
        return [
          [
            [w, s],
            [e, s],
            [e, n],
            [w, n],
            [w, s],
          ],
        ];
      })()
    : [];
  return [
    new ScatterplotLayer<ConflictRegion>({
      id: 'conflict-region-selection',
      data: selectedData,
      getPosition: (item) => item.centre,
      getRadius: 22,
      radiusUnits: 'pixels',
      filled: false,
      stroked: true,
      getLineColor: [126, 227, 240, 255],
      getLineWidth: 2,
      lineWidthUnits: 'pixels',
      pickable: false,
    }),
    new PathLayer<Position[]>({
      id: 'conflict-region-context',
      data: outline,
      getPath: (path) => path,
      getColor: [126, 227, 240, 120],
      getWidth: 1,
      widthUnits: 'pixels',
      wrapLongitude: flat,
      pickable: false,
    }),
    new ScatterplotLayer<ConflictRegion>({
      id: 'conflict-region-badges',
      data: regions,
      getPosition: (item) => item.centre,
      getRadius: 18,
      radiusUnits: 'pixels',
      filled: true,
      stroked: true,
      getFillColor: [10, 14, 21, 240],
      getLineColor: colour,
      getLineWidth: 1,
      lineWidthUnits: 'pixels',
      pickable,
      onClick: selectRegion,
    }),
    new IconLayer<ConflictRegion>({
      id: 'conflict-region-markers',
      data: regions,
      billboard: flat,
      parameters: SYMBOL_WINDING,
      getAngle: flat ? 0 : 180,
      getPosition: (item) => item.centre,
      getIcon: (item) => ({
        url: CONFLICT_REGION_MARKERS[item.card.conflict.status === 'war' ? 'war' : 'tension'],
        width: 64,
        height: 64,
        mask: true,
      }),
      getColor: colour,
      getSize: (item) => (item.card.conflict.id === selected?.card.conflict.id ? 31 : 27),
      sizeUnits: 'pixels',
      updateTriggers: { getSize: [selected?.card.conflict.id] },
      pickable,
      onClick: selectRegion,
    }),
    new TextLayer<ConflictRegion>({
      id: 'conflict-region-labels',
      data: selectedData,
      billboard: flat,
      parameters: SYMBOL_WINDING,
      getAngle: flat ? 0 : 180,
      getPosition: (item) => item.centre,
      getText: (item) => item.card.conflict.name,
      getSize: 11,
      getColor: colour,
      getPixelOffset: [0, 25],
      background: true,
      getBackgroundColor: [7, 10, 14, 220],
      getTextAnchor: 'middle',
      pickable: false,
    }),
  ];
}
