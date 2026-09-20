import { TextLayer } from '@deck.gl/layers';
import { drawingLayers } from './drawingLayers';
import { drawingVertices } from './drawingGeometry';
import type { DrawingObject } from './drawingCollection';
import type { Layer } from '@deck.gl/core';

export function drawingCollectionLayers(objects: readonly DrawingObject[], flat: boolean): Layer[] {
  return objects
    .filter((item) => item.visible)
    .flatMap((item) => {
      const colour = [1, 3, 5].map((offset) => parseInt(item.colour.slice(offset, offset + 2), 16));
      const points =
        item.shape === 'point' ? item.anchors : drawingVertices(item.shape, item.anchors);
      const layers = drawingLayers(
        points,
        item.shape === 'point' || item.shape === 'path' ? 'distance' : 'area',
        flat,
        item.shape === 'point' ? item.anchors : [],
      ).map(
        (layer) =>
          (layer as Layer).clone({
            id: `object-${item.id}-${layer.id}`,
            ...(layer.id.includes('fill')
              ? { getFillColor: [...colour, 40] }
              : layer.id.includes('points')
                ? { getFillColor: [...colour, 255] }
                : { getColor: [...colour, 240] }),
          }) as Layer,
      );
      const position = item.anchors[0];
      if (position && (!flat || Math.abs(position[1]) <= 85))
        layers.push(
          new TextLayer({
            id: `object-label-${item.id}`,
            data: [{ position, name: item.name }],
            getPosition: (entry: { position: [number, number] }) => entry.position,
            getText: (entry: { name: string }) => entry.name,
            getColor: [colour[0] ?? 0, colour[1] ?? 0, colour[2] ?? 0, 255],
            getSize: 13,
            getPixelOffset: [0, -18],
            billboard: true,
            pickable: false,
          }),
        );
      return layers;
    });
}
