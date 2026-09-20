import { IconLayer, ScatterplotLayer } from '@deck.gl/layers';
import type { Layer, PickingInfo } from '@deck.gl/core';

import { portraitUrl, type PlacementBasis, type PublicFigure } from '@/lib/api/figures';
import { SYMBOL_WINDING } from '@/lib/map/symbolWinding';

// IconLayer masks use alpha, so the area around the head and shoulders must be transparent.
const FALLBACK = `data:image/svg+xml;utf8,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><circle cx="32" cy="25" r="10" fill="white"/><path d="M14 52a18 18 0 0 1 36 0z" fill="white"/></svg>')}`;

export const BASIS_COLOURS: Record<PlacementBasis, [number, number, number, number]> = {
  reported_place: [98, 222, 190, 255],
  reported_country: [245, 196, 98, 255],
  seat: [150, 160, 175, 210],
};

/** Circular portraits ringed by the placement basis, so a default never looks like a sighting. */
export function buildFigureLayers(
  figures: readonly PublicFigure[],
  onSelect: (figure: PublicFigure) => void,
  selectedId: string | null,
  globe = false,
): Layer[] {
  // Shared seats remain geographically accurate. A separate last pass keeps the selection
  // above both portrait and fallback neighbours without depending on roster order.
  const others = figures.filter((figure) => figure.id !== selectedId);
  const selected = figures.filter((figure) => figure.id === selectedId);
  return [
    ...figureMarkerGroup(others, onSelect, selectedId, globe, 'public-figure'),
    ...figureMarkerGroup(selected, onSelect, selectedId, globe, 'public-figure-selected'),
  ];
}

function figureMarkerGroup(
  figures: readonly PublicFigure[],
  onSelect: (figure: PublicFigure) => void,
  selectedId: string | null,
  globe: boolean,
  prefix: string,
): Layer[] {
  if (!figures.length) return [];
  const size = (figure: PublicFigure) => (figure.id === selectedId ? 40 : 30);
  const position = (figure: PublicFigure): [number, number] => [
    figure.placement.longitude,
    figure.placement.latitude,
  ];
  const withPortrait = figures.filter((figure) => figure.portrait !== null);
  const withoutPortrait = figures.filter((figure) => figure.portrait === null);
  const layers: Layer[] = [
    new ScatterplotLayer<PublicFigure>({
      id: `${prefix}-rings`,
      data: figures,
      pickable: true,
      stroked: true,
      filled: true,
      radiusUnits: 'pixels',
      lineWidthUnits: 'pixels',
      getPosition: position,
      getRadius: (figure) => size(figure) / 2 + 2,
      getLineWidth: (figure) => (figure.id === selectedId ? 3 : 2),
      getFillColor: [10, 14, 22, 220],
      getLineColor: (figure) => BASIS_COLOURS[figure.placement.basis],
      updateTriggers: { getRadius: [selectedId], getLineWidth: [selectedId] },
      onClick: (info: PickingInfo<PublicFigure>) => {
        if (info.object) onSelect(info.object);
        return true;
      },
    }),
  ];
  if (withPortrait.length)
    layers.push(
      new IconLayer<PublicFigure>({
        id: `${prefix}-portraits`,
        data: withPortrait,
        pickable: true,
        billboard: !globe,
        parameters: SYMBOL_WINDING,
        getPosition: position,
        getIcon: (figure) => ({
          url: portraitUrl(figure) ?? FALLBACK,
          id: figure.wikidata_id,
          width: 64,
          height: 64,
          mask: false,
        }),
        sizeUnits: 'pixels',
        getSize: size,
        getAngle: globe ? 180 : 0,
        updateTriggers: { getSize: [selectedId] },
        onClick: (info: PickingInfo<PublicFigure>) => {
          if (info.object) onSelect(info.object);
          return true;
        },
      }),
    );
  if (withoutPortrait.length)
    layers.push(
      new IconLayer<PublicFigure>({
        id: `${prefix}-fallbacks`,
        data: withoutPortrait,
        pickable: true,
        billboard: !globe,
        parameters: SYMBOL_WINDING,
        getPosition: position,
        getIcon: () => ({ url: FALLBACK, width: 64, height: 64, mask: true }),
        sizeUnits: 'pixels',
        getSize: size,
        getColor: [220, 226, 235, 255],
        getAngle: globe ? 180 : 0,
        updateTriggers: { getSize: [selectedId] },
        onClick: (info: PickingInfo<PublicFigure>) => {
          if (info.object) onSelect(info.object);
          return true;
        },
      }),
    );
  return layers;
}
