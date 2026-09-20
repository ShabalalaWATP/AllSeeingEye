import type { Layer, PickingInfo } from '@deck.gl/core';
import { describe, expect, it, vi } from 'vitest';
import type { PublicFigure } from '@/lib/api/figures';
import { publicFigure } from '@/test/fixtures.figures';
import { buildFigureLayers } from './figureLayers';

function occupants(portrait: boolean) {
  const selected = publicFigure({
    id: 'selected',
    ...(portrait ? {} : { portrait: null }),
  });
  return [
    selected,
    publicFigure({ id: 'other-portrait', wikidata_id: 'Q123' }),
    publicFigure({ id: 'other-fallback', wikidata_id: 'Q456', portrait: null }),
  ];
}

function rows(layer: Layer): readonly PublicFigure[] {
  return layer.props.data as readonly PublicFigure[];
}

interface SymbolAccessors {
  getPosition: (figure: PublicFigure) => number[];
  getSize: (figure: PublicFigure) => number;
  getIcon: (figure: PublicFigure) => { url: string; mask: boolean };
}

describe('overlapping public figure symbols', () => {
  it.each([false, true])(
    'renders the selected figure above every neighbour (portrait=%s)',
    (portrait) => {
      const figures = occupants(portrait);
      const onSelect = vi.fn();
      const layers = buildFigureLayers(figures, onSelect, 'selected', true);
      const foreground = layers.slice(-2);
      expect(foreground.map((layer) => layer.id)).toEqual([
        'public-figure-selected-rings',
        portrait ? 'public-figure-selected-portraits' : 'public-figure-selected-fallbacks',
      ]);
      for (const layer of layers.slice(0, -2)) {
        expect(rows(layer).some((figure) => figure.id === 'selected')).toBe(false);
      }
      for (const layer of foreground) expect(rows(layer)).toEqual([figures[0]]);
      const symbol = foreground[1]!;
      const accessors = symbol.props as unknown as SymbolAccessors;
      expect(accessors.getPosition(figures[0]!)).toEqual([36.23, 49.99]);
      expect(accessors.getSize(figures[0]!)).toBe(40);
      symbol.props.onClick?.({ object: figures[0] } as PickingInfo<PublicFigure>, {} as never);
      expect(onSelect).toHaveBeenCalledExactlyOnceWith(figures[0]);
    },
  );

  it('uses a transparent silhouette instead of an opaque background as the fallback mask', () => {
    const figure = publicFigure({ portrait: null });
    const layer = buildFigureLayers([figure], vi.fn(), null).at(-1)!;
    const icon = (layer.props as unknown as SymbolAccessors).getIcon(figure);
    const svg = new DOMParser().parseFromString(
      decodeURIComponent(icon.url.split(',')[1]!),
      'image/svg+xml',
    );
    expect(icon.mask).toBe(true);
    // A mask ignores RGB. A full opaque circle would erase the silhouette detail.
    expect(svg.querySelectorAll('circle')).toHaveLength(1);
    expect(svg.querySelector('circle')?.getAttribute('r')).toBe('10');
    expect(svg.querySelector('path')).not.toBeNull();
    expect(svg.querySelector('rect')).toBeNull();
  });

  it('does not add stale selection layers when a selected figure is filtered out', () => {
    const layers = buildFigureLayers(occupants(true).slice(1), vi.fn(), 'selected');
    expect(layers.every((layer) => !layer.id.includes('-selected-'))).toBe(true);
    for (const layer of layers) {
      expect(rows(layer).every((figure) => figure.id !== 'selected')).toBe(true);
    }
  });
});
