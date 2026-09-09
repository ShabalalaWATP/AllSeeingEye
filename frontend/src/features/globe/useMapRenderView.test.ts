import { act, renderHook } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import type { ViewMode } from '@/stores/globe';
import type { ViewHandler } from './useGlobeEngine';
import { useMapRenderView } from './useMapRenderView';

function camera(initialZoom: number) {
  let zoom = initialZoom;
  const handlers = new Set<ViewHandler>();
  return {
    getZoom: () => zoom,
    onView: (handler: ViewHandler) => {
      handlers.add(handler);
      return () => {
        handlers.delete(handler);
      };
    },
    move(next: number) {
      zoom = next;
      for (const handler of handlers) handler({ zoom });
    },
    handlers,
  };
}

it('tracks the real projection boundary both ways while retaining coarse clustering zoom', () => {
  const engine = camera(12);
  const { result, rerender, unmount } = renderHook(
    ({ mode }: { mode: ViewMode }) => useMapRenderView(engine, mode),
    { initialProps: { mode: 'globe' } },
  );
  expect(result.current).toEqual({ zoom: 3, symbolMode: 'globe' });
  act(() => engine.move(12.01));
  expect(result.current).toEqual({ zoom: 3, symbolMode: 'map' });
  act(() => engine.move(11.99));
  expect(result.current).toEqual({ zoom: 3, symbolMode: 'globe' });
  rerender({ mode: 'map' });
  expect(result.current).toEqual({ zoom: 3, symbolMode: 'map' });
  rerender({ mode: 'globe' });
  expect(result.current).toEqual({ zoom: 3, symbolMode: 'globe' });
  unmount();
  expect(engine.handlers.size).toBe(0);
});

it('does not rerender the dashboard for camera movement inside the same render bands', () => {
  const engine = camera(1.5);
  const render = vi.fn();
  const { result } = renderHook(() => {
    render();
    return useMapRenderView(engine, 'globe');
  });
  const first = result.current;
  const count = render.mock.calls.length;
  for (const zoom of [1.5, 1.6, 1.8, 2, 2.49]) act(() => engine.move(zoom));
  expect(result.current).toBe(first);
  expect(render).toHaveBeenCalledTimes(count);
  act(() => engine.move(2.5));
  expect(result.current.zoom).toBe(2.5);
  act(() => engine.move(3));
  const unclustered = result.current;
  const unclusteredCount = render.mock.calls.length;
  for (const zoom of [4, 6, 8, 10, 12]) act(() => engine.move(zoom));
  expect(result.current).toBe(unclustered);
  expect(render).toHaveBeenCalledTimes(unclusteredCount);
});

it('reads an existing close-up camera and resubscribes when the engine changes', () => {
  const first = camera(14);
  const second = camera(2);
  const { result, rerender } = renderHook(({ engine }) => useMapRenderView(engine, 'globe'), {
    initialProps: { engine: first },
  });
  expect(result.current).toEqual({ zoom: 3, symbolMode: 'map' });
  rerender({ engine: second });
  expect(first.handlers.size).toBe(0);
  expect(second.handlers.size).toBe(1);
  expect(result.current).toEqual({ zoom: 1.5, symbolMode: 'globe' });
});
