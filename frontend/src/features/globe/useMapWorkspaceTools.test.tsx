import { act, render, renderHook, fireEvent, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { RfCalculatorPanel } from '@/components/maps/RfCalculatorPanel';
import { rfMapEstimate } from '@/lib/map/rfMap';
import { DEFAULT_RF_INPUTS } from '@/lib/map/rfPlanning';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser } from '@/test/fixtures';
import { useMapWorkspaceTools } from './useMapWorkspaceTools';
import type { GlobeEngineHandle } from './useGlobeEngine';

function fakeEngine() {
  const handlers = new Set<(point: { lon: number; lat: number }) => void>();
  const engine: GlobeEngineHandle = {
    setLayers: vi.fn(),
    flyTo: vi.fn(),
    getZoom: () => 4,
    spin: vi.fn(),
    onCursor: () => () => undefined,
    onView: () => () => undefined,
    setSketchMode: vi.fn(),
    onClick: (handler: (point: { lon: number; lat: number }) => void) => {
      handlers.add(handler);
      return () => {
        handlers.delete(handler);
      };
    },
  };
  return {
    engine,
    click: (lon = 1, lat = 2) => handlers.forEach((handler) => handler({ lon, lat })),
    listeners: () => handlers.size,
  };
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

it('stops measuring on close and transfers click ownership without discarding points', () => {
  const { engine, click } = fakeEngine();
  const { result } = renderHook(() => useMapWorkspaceTools(engine, true, 'map'));
  act(() => result.current.measurement.setPicking(true));
  act(click);
  act(() => result.current.activatePanel(null));
  expect(result.current.measurement.picking).toBe(false);
  act(click);
  expect(result.current.measurement.points).toHaveLength(1);
  act(() => result.current.measurement.setPicking(true));
  act(() => result.current.activatePanel('Route planner'));
  expect(result.current.picking).toBe(false);
  act(() => result.current.drawing.setPicking(true));
  act(() => result.current.activatePanel(null));
  expect(result.current.picking).toBe(false);
});

it('gives RF exclusive click ownership and transfers it back to measuring or drawing', () => {
  const { engine, click } = fakeEngine();
  const { result } = renderHook(() => useMapWorkspaceTools(engine, true, 'map'));
  act(() => result.current.measurement.setPicking(true));
  act(() => result.current.rf.setPicking('origin'));
  expect(result.current.measurement.picking).toBe(false);
  expect(result.current.drawing.picking).toBe(false);
  expect(engine.setSketchMode).toHaveBeenLastCalledWith('points');
  act(() => click(-0.1, 51.5));
  expect(result.current.rf.origin).toEqual([-0.1, 51.5]);
  expect(result.current.measurement.points).toEqual([]);
  expect(result.current.drawing.points).toEqual([]);
  expect(result.current.picking).toBe(false);
  expect(engine.setSketchMode).toHaveBeenLastCalledWith('navigate');
  act(() => result.current.rf.setPicking('receiver'));
  act(() => result.current.drawing.setPicking(true));
  expect(result.current.rf.picking).toBeNull();
  act(() => click(0.1, 51.5));
  expect(result.current.drawing.points).toEqual([[0.1, 51.5]]);
  expect(result.current.rf.receiver).toBeNull();
  act(() => result.current.rf.setPicking('receiver'));
  act(() => result.current.measurement.setPicking(true));
  expect(result.current.rf.picking).toBeNull();
  expect(result.current.drawing.picking).toBe(false);
});

it('renders a circle and link from RF positions, then clears stale output when positions or fields change', () => {
  const { engine, click } = fakeEngine();
  const { result } = renderHook(() => useMapWorkspaceTools(engine, true, 'map'));
  act(() => result.current.rf.setPicking('origin'));
  act(() => click(0, 51));
  act(() => result.current.rf.setPicking('receiver'));
  act(() => click(0.1, 51));
  const estimate = rfMapEstimate(DEFAULT_RF_INPUTS, [0, 51], [0.1, 51]);
  act(() => result.current.rf.setEstimate(estimate));
  const path = result.current.layers.find((layer) => layer.id === 'rf-estimate-paths');
  expect(path?.props.data).toHaveLength(2);
  expect(result.current.layers.some((layer) => layer.id === 'rf-estimate-label')).toBe(true);
  act(() => result.current.rf.setPicking('receiver'));
  act(() => click(0.2, 51));
  expect(result.current.rf.receiver).toEqual([0.2, 51]);
  expect(result.current.rf.estimate).toBeNull();
  expect(result.current.layers.some((layer) => layer.id.startsWith('rf-'))).toBe(false);
  act(() => result.current.rf.setEstimate(estimate));
  render(<RfCalculatorPanel origin={[0, 51]} onOverlayChange={result.current.rf.setEstimate} />);
  fireEvent.change(screen.getByRole('combobox', { name: 'Propagation model' }), {
    target: { value: 'free-space' },
  });
  fireEvent.change(screen.getByLabelText('Frequency (MHz)'), { target: { value: '150' } });
  expect(result.current.rf.estimate).toBeNull();
  expect(result.current.layers.some((layer) => layer.id.startsWith('rf-'))).toBe(false);
});

it.each(['access', 'account'] as const)('clears RF positions and output on %s change', (change) => {
  useAuthStore.setState({ user: plainUser, status: 'authenticated' });
  const { engine, click } = fakeEngine();
  const { result } = renderHook(() => useMapWorkspaceTools(engine, true, 'map'));
  act(() => result.current.rf.setPicking('origin'));
  act(() => click(0, 51));
  act(() => result.current.rf.setPicking('receiver'));
  act(() => click(0.1, 51));
  act(() => result.current.rf.setEstimate(rfMapEstimate(DEFAULT_RF_INPUTS, [0, 51], [0.1, 51])));
  act(() => result.current.rf.setPicking('origin'));
  act(() => {
    if (change === 'access') invalidateWorkspaceAccess();
    else useAuthStore.setState({ user: adminUser });
  });
  expect(result.current.rf.origin).toBeNull();
  expect(result.current.rf.receiver).toBeNull();
  expect(result.current.rf.estimate).toBeNull();
  expect(result.current.rf.picking).toBeNull();
  expect(result.current.layers.some((layer) => layer.id.startsWith('rf-'))).toBe(false);
  act(() => click(1, 52));
  expect(result.current.rf.origin).toBeNull();
});

it('cancels RF on Escape, panel closure and disabling without resuming invisibly', () => {
  const { engine, click, listeners } = fakeEngine();
  const { result, rerender, unmount } = renderHook(
    ({ enabled }) => useMapWorkspaceTools(engine, enabled, 'map'),
    { initialProps: { enabled: true } },
  );
  act(() => result.current.rf.setPicking('origin'));
  act(() => click(NaN, 91));
  expect(result.current.rf.picking).toBe('origin');
  expect(result.current.rf.origin).toBeNull();
  fireEvent.keyDown(window, { key: 'Escape' });
  expect(result.current.picking).toBe(false);
  act(() => result.current.rf.setPicking('origin'));
  act(() => result.current.activatePanel('RF link calculator'));
  expect(result.current.rf.picking).toBe('origin');
  act(() => result.current.activatePanel(null));
  expect(result.current.picking).toBe(false);
  act(() => result.current.rf.setPicking('receiver'));
  act(() => result.current.activatePanel('Route planner'));
  expect(result.current.picking).toBe(false);
  act(() => result.current.rf.setPicking('origin'));
  rerender({ enabled: false });
  rerender({ enabled: true });
  expect(result.current.picking).toBe(false);
  act(() => click(0, 51));
  expect(result.current.rf.origin).toBeNull();
  unmount();
  expect(listeners()).toBe(0);
});
