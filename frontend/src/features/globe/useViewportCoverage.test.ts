import { act, renderHook } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { useEventsStore } from '@/stores/events';
import { useViewportCoverage } from './useViewportCoverage';
import type { GlobeEngineHandle, ViewHandler } from './useGlobeEngine';

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
  useEventsStore.getState().reset();
});

it('debounces settled viewport changes, returns to global on zoom out and stops while hidden', () => {
  vi.useFakeTimers();
  useEventsStore.getState().reset();
  const load = vi.spyOn(useEventsStore.getState(), 'load').mockResolvedValue();
  let move: ViewHandler = () => undefined;
  let zoom = 4;
  const off = vi.fn();
  const engine: GlobeEngineHandle = {
    getZoom: () => zoom,
    getViewportBounds: () => ({ west: 100, east: 150, north: 40, south: -40 }),
    onView: (handler) => {
      move = handler;
      return off;
    },
    setLayers: vi.fn(),
    flyTo: vi.fn(),
    spin: vi.fn(),
    onCursor: () => vi.fn(),
    onClick: () => vi.fn(),
  };
  const { rerender, unmount } = renderHook(({ enabled }) => useViewportCoverage(engine, enabled), {
    initialProps: { enabled: true },
  });
  act(() => {
    vi.advanceTimersByTime(700);
    move({ zoom });
    vi.advanceTimersByTime(700);
  });
  expect(load).not.toHaveBeenCalled();
  act(() => {
    vi.advanceTimersByTime(100);
  });
  expect(load).toHaveBeenCalledOnce();
  expect(useEventsStore.getState().coverageBounds).toEqual([100, -40, 150, 40]);
  act(() => {
    move({ zoom });
    vi.advanceTimersByTime(800);
  });
  expect(load).toHaveBeenCalledOnce();
  zoom = 1;
  act(() => {
    move({ zoom });
    vi.advanceTimersByTime(800);
  });
  expect(useEventsStore.getState().coverageBounds).toBeNull();
  expect(load).toHaveBeenCalledTimes(2);
  act(() => move({ zoom: 4 }));
  rerender({ enabled: false });
  act(() => {
    vi.advanceTimersByTime(800);
  });
  expect(load).toHaveBeenCalledTimes(2);
  unmount();
  expect(off).toHaveBeenCalledOnce();
});
