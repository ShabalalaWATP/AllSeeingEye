import { act, renderHook } from '@testing-library/react';
import { expect, it, vi } from 'vitest';

import { useBritishGrid } from './useBritishGrid';
import type { GlobeEngineHandle, ViewHandler } from './useGlobeEngine';

it('starts disabled, draws a non-pickable grid at current zoom and cleans up its subscription', () => {
  let move: ViewHandler = () => undefined;
  const unsubscribe = vi.fn();
  const engine: GlobeEngineHandle = {
    setLayers: vi.fn(),
    flyTo: vi.fn(),
    spin: vi.fn(),
    onCursor: () => () => undefined,
    onClick: () => () => undefined,
    getZoom: () => 8,
    onView: (handler: ViewHandler) => {
      move = handler;
      return unsubscribe;
    },
  };
  const { result, unmount } = renderHook(() => useBritishGrid(engine));
  expect(result.current.layers).toHaveLength(0);
  act(() => result.current.setEnabled(true));
  expect(result.current.layers).toHaveLength(1);
  const layer = result.current.layers[0]!;
  expect(layer.props.pickable).toBe(false);
  expect(layer.props.data).toHaveLength(202);
  act(() => move({ zoom: 3 }));
  expect(result.current.layers).toHaveLength(0);
  act(() => move({ zoom: 5.5 }));
  expect(result.current.layers[0]!.props.data).toHaveLength(22);
  act(() => result.current.setEnabled(false));
  expect(result.current.layers).toHaveLength(0);
  unmount();
  expect(unsubscribe).toHaveBeenCalledOnce();
});
