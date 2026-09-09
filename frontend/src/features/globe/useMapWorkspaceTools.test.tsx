import { act, renderHook } from '@testing-library/react';
import { expect, it } from 'vitest';
import { useMapWorkspaceTools } from './useMapWorkspaceTools';
import type { GlobeEngineHandle } from './useGlobeEngine';

function fakeEngine() {
  const handlers = new Set<(point: { lon: number; lat: number }) => void>();
  const engine = {
    onClick: (handler: (point: { lon: number; lat: number }) => void) => {
      handlers.add(handler);
      return () => {
        handlers.delete(handler);
      };
    },
  } as GlobeEngineHandle;
  return { engine, click: () => handlers.forEach((handler) => handler({ lon: 1, lat: 2 })) };
}

it.each(['measurement', 'drawing'] as const)(
  'disabling tools stops %s picking without discarding points or resuming invisibly',
  (owner) => {
    const { engine, click } = fakeEngine();
    const { result, rerender } = renderHook(
      ({ enabled }) => useMapWorkspaceTools(engine, enabled, 'map'),
      { initialProps: { enabled: true } },
    );
    act(() => result.current[owner].setPicking(true));
    act(click);
    expect(result.current[owner].points).toHaveLength(1);
    rerender({ enabled: false });
    expect(result.current.picking).toBe(false);
    rerender({ enabled: true });
    expect(result.current.picking).toBe(false);
    act(click);
    expect(result.current[owner].points).toHaveLength(1);
  },
);

it('preserves close-panel measuring but transfers click ownership to other panels', () => {
  const { engine } = fakeEngine();
  const { result } = renderHook(() => useMapWorkspaceTools(engine, true, 'map'));
  act(() => result.current.measurement.setPicking(true));
  act(() => result.current.activatePanel(null));
  expect(result.current.measurement.picking).toBe(true);
  act(() => result.current.activatePanel('Route planner'));
  expect(result.current.picking).toBe(false);
  act(() => result.current.drawing.setPicking(true));
  act(() => result.current.activatePanel(null));
  expect(result.current.picking).toBe(false);
});
