import { act, renderHook } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { useMapMeasurement } from './useMapMeasurement';
import { measurementLayers } from '@/lib/map/measurementLayers';
import type { Position } from '@/lib/map/geoJsonTypes';

it('caps batched coordinate submissions and rejects invalid numeric input', () => {
  const engine = { onClick: vi.fn(() => vi.fn()) };
  const view = renderHook(() => useMapMeasurement(engine, true));
  act(() => view.result.current.add(NaN, 0));
  expect(view.result.current.error).toContain('Enter longitude');
  act(() => {
    for (let i = 0; i < 40; i++) view.result.current.add(i, 0);
  });
  expect(view.result.current.points).toHaveLength(32);
  act(() => view.result.current.add(60, 0));
  expect(view.result.current.error).toContain('At most 32');
});

it('omits polar drawing in flat view without changing coordinates or joining across the omitted portion', () => {
  const points: Position[] = [
    [0, 89],
    [120, 89],
    [-120, 89],
  ];
  const flat = measurementLayers(points, 'area', true);
  expect(flat[0]?.props.data).toEqual([]);
  expect(flat[1]?.props.data).toEqual([]);
  const globe = measurementLayers(points, 'area', false);
  expect(globe[0]?.props.data).toHaveLength(3);
  expect(globe[1]?.props.data).toEqual(points);
  expect(globe[0]?.props.pickable).toBe(false);
  expect(measurementLayers([], 'distance', true)).toEqual([]);
});
