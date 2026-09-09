import { IconLayer, PathLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers';
import type { Layer, PickingInfo } from '@deck.gl/core';
import type { ConflictRegion } from '../conflictRegions';
import type { Position } from '@/lib/map/geoJsonTypes';

const marker =
  'data:image/svg+xml,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24"><path d="m3 3 5 1 11 11-4 4L4 8 3 3Zm18 0-5 1-4 4m-3 5-4 4m-3-3 7 7m5-7 7 7M3 21l3-3m12 0 3 3" stroke="white" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round" fill="none"/></svg>',
  );
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
    new IconLayer<ConflictRegion>({
      id: 'conflict-region-markers',
      data: regions,
      getPosition: (item) => item.centre,
      getIcon: () => ({ url: marker, width: 32, height: 32, mask: true }),
      getColor: colour,
      getSize: 27,
      sizeUnits: 'pixels',
      pickable,
      onClick: ({ object }: PickingInfo<ConflictRegion>) => {
        if (object) onSelect(object);
        return true;
      },
    }),
    new TextLayer<ConflictRegion>({
      id: 'conflict-region-labels',
      data: selectedData,
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
