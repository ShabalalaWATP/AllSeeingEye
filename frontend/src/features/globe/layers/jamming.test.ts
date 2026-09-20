import { expect, it } from 'vitest';
import { jamMap } from '@/test/fixtures';
import { useGlobeStore } from '@/stores/globe';
import { buildJamLayer, cellPolygon } from './jamming';

it('draws only the amber and red interference cells as squares', () => {
  const layer = buildJamLayer(jamMap.cells);
  expect(layer?.id).toBe('gnss-interference');
  const props = layer!.props as unknown as {
    data: unknown[];
    getFillColor: (cell: { level: string }) => number[];
  };
  expect(props.data).toHaveLength(2);
  expect(props.getFillColor({ level: 'red' })[0]).toBe(255);
  expect(props.getFillColor({ level: 'amber' })[1]).toBe(181);
  expect(buildJamLayer([jamMap.cells[2]!])).toBeNull();
  expect(cellPolygon(jamMap.cells[0]!)).toEqual([
    [36, 49],
    [37, 49],
    [37, 50],
    [36, 50],
    [36, 49],
  ]);
  useGlobeStore.getState().toggleInterference();
  expect(useGlobeStore.getState().interference).toBe(true);
  useGlobeStore.getState().toggleInterference();
});
