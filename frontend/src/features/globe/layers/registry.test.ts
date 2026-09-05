import { describe, expect, it, vi } from 'vitest';

import { liveEvent } from '@/test/fixtures';

import { CATEGORY_STYLES, ORDERED_CATEGORIES } from '@/lib/categories';
import { buildEventLayers, radiusFor } from './registry';

describe('layer registry', () => {
  it('orders categories and gives each a colour', () => {
    expect(ORDERED_CATEGORIES[0]).toBe('disaster');
    expect(ORDERED_CATEGORIES).toHaveLength(Object.keys(CATEGORY_STYLES).length);
    for (const style of Object.values(CATEGORY_STYLES)) {
      expect(style.colour).toHaveLength(3);
      expect(style.css).toMatch(/^#[0-9a-f]{6}$/);
    }
  });

  it('scales the radius with severity and floors it', () => {
    expect(radiusFor(liveEvent({ severity: null }))).toBeCloseTo(4.8);
    expect(radiusFor(liveEvent({ severity: 0 }))).toBe(3);
    expect(radiusFor(liveEvent({ severity: 1 }))).toBe(12);
    expect(radiusFor(liveEvent({ severity: 5 }))).toBe(12);
  });

  it('builds one layer per visible category with located events only', () => {
    const onPick = vi.fn();
    const events = [
      liveEvent({ id: 'a' }),
      liveEvent({ id: 'b', category: 'cyber', point: null }),
      liveEvent({ id: 'c', category: 'space', point: { lon: 1, lat: 2 } }),
      liveEvent({ id: 'd', category: 'space', point: { lon: 3, lat: 4 } }),
    ];
    const layers = buildEventLayers(events, ['disaster'], onPick, 'd');
    expect(layers.map((layer) => layer.id)).toEqual(['events-space']);
    const layer = layers[0]!;
    const props = layer.props as unknown as {
      data: unknown[];
      getPosition: (e: unknown) => [number, number];
      getRadius: (e: unknown) => number;
      getFillColor: (e: unknown) => number[];
      getLineColor: (e: unknown) => number[];
      onClick: (info: { object?: unknown }) => boolean;
    };
    expect(props.data).toHaveLength(2);
    expect(props.getPosition(events[2])).toEqual([1, 2]);
    expect(props.getRadius(events[3])).toBeGreaterThan(props.getRadius(events[2]));
    expect(props.getFillColor(events[3])[3]).toBe(255);
    expect(props.getLineColor(events[2])).toEqual([7, 7, 11, 200]);
    expect(props.onClick({ object: events[2] })).toBe(true);
    expect(onPick).toHaveBeenCalledWith(events[2]);
    props.onClick({});
    expect(onPick).toHaveBeenLastCalledWith(null);
  });
});
