import { renderHook } from '@testing-library/react';
import { ScatterplotLayer } from '@deck.gl/layers';
import { expect, it } from 'vitest';
import { useGlobeLayerGroups } from './useGlobeLayerGroups';

it('keeps the dashboard draw order and memoised groups until a catalogue changes', () => {
  const layer = (id: string) => [new ScatterplotLayer({ id })];
  const props = {
    grid: layer('grid'),
    infrastructure: layer('infrastructure'),
    regions: layer('regions'),
    cameras: layer('cameras'),
    figures: layer('figures'),
    context: layer('context'),
    cyber: layer('cyber'),
    radar: layer('radar'),
    network: layer('network'),
    news: layer('news'),
    tools: layer('tools'),
  };
  const { result, rerender } = renderHook(useGlobeLayerGroups, { initialProps: props });
  const before = result.current;
  expect(
    before.flatMap((group) => (group === 'events' ? group : group.map((entry) => entry.id))),
  ).toEqual([
    'grid',
    'infrastructure',
    'events',
    'regions',
    'cameras',
    'figures',
    'context',
    'cyber',
    'radar',
    'network',
    'news',
    'tools',
  ]);
  rerender({ ...props });
  expect(result.current).toBe(before);
  rerender({ ...props, network: [] });
  expect(result.current).not.toBe(before);
  expect(result.current[9]).toEqual([]);
});
