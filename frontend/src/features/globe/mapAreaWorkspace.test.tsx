import { act, fireEvent, render, renderHook, screen } from '@testing-library/react';
import { it, expect, vi } from 'vitest';
import type { GlobeEngineHandle } from './useGlobeEngine';
import { useMapWorkspaceTools } from './useMapWorkspaceTools';
import { MapResearchDrawingControls } from './MapResearchDrawingControls';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';

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
    onClick: (handler) => {
      handlers.add(handler);
      return () => {
        handlers.delete(handler);
      };
    },
  };
  return {
    engine,
    click: (lon: number, lat: number) => handlers.forEach((fn) => fn({ lon, lat })),
  };
}

it('gives area research exclusive map input and only submits committed finished geometry', () => {
  const { engine, click } = fakeEngine();
  const { result } = renderHook(() => useMapWorkspaceTools(engine, true, 'globe'));
  act(() => result.current.measurement.setPicking(true));
  act(() => result.current.research.drawing.setPicking(true));
  expect(result.current.measurement.picking).toBe(false);
  act(() => {
    click(0, 0);
    click(2, 0);
    click(0, 2);
  });
  expect(result.current.research.area).toBeNull();
  expect(result.current.research.drawing.anchors).toHaveLength(3);
  expect(result.current.measurement.points).toEqual([]);
  act(() => result.current.research.drawing.setPicking(false));
  expect(result.current.research.area?.features).toHaveLength(1);
  expect(result.current.layers.some((layer) => layer.id === 'research-area-boundary')).toBe(true);
  act(() => result.current.research.drawing.setPicking(true));
  act(() => result.current.rf.setPicking('origin'));
  expect(result.current.research.drawing.picking).toBe(false);
  act(() => result.current.research.drawing.setPicking(true));
  expect(result.current.rf.picking).toBeNull();
  act(() => result.current.drawing.setPicking(true));
  expect(result.current.research.drawing.picking).toBe(false);
  act(() => result.current.research.drawing.setPicking(true));
  act(() => result.current.activatePanel(null));
  expect(result.current.research.drawing.picking).toBe(false);
  act(() => result.current.research.drawing.setPicking(true));
  act(() => result.current.measurement.setPicking(true));
  expect(result.current.research.drawing.picking).toBe(false);
  act(invalidateWorkspaceAccess);
  expect(result.current.research.area).toBeNull();
  expect(result.current.research.drawing.anchors).toEqual([]);
});

it('stops area input when the map becomes unavailable and explains invalid areas', () => {
  const { engine, click } = fakeEngine();
  const { result, rerender } = renderHook(
    ({ enabled }) => useMapWorkspaceTools(engine, enabled, 'map'),
    { initialProps: { enabled: true } },
  );
  act(() => result.current.research.drawing.setPicking(true));
  act(() => {
    click(0, 0);
    click(2, 2);
  });
  rerender({ enabled: false });
  expect(result.current.picking).toBe(false);
  expect(result.current.research.area).toBeNull();
  expect(result.current.research.areaError).toContain('three corners');
  rerender({ enabled: true });
  expect(result.current.picking).toBe(false);
});

it('offers only area shapes, supports click drawing and clears the selection', () => {
  const { engine, click } = fakeEngine();
  function Harness() {
    const tools = useMapWorkspaceTools(engine, true, 'map');
    return <MapResearchDrawingControls value={tools.research.drawing} />;
  }
  render(<Harness />);
  expect(screen.queryByRole('button', { name: 'Path' })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Rectangle' }));
  expect(engine.setSketchMode).toHaveBeenLastCalledWith('points');
  act(() => {
    click(0, 0);
    click(2, 2);
  });
  expect(screen.getByRole('button', { name: 'Redraw area' })).toBeEnabled();
  fireEvent.click(screen.getByRole('button', { name: 'Undo point' }));
  fireEvent.click(screen.getByRole('button', { name: 'Draw boundary' }));
  fireEvent.click(screen.getByRole('button', { name: 'Finish boundary' }));
  fireEvent.click(screen.getByRole('button', { name: 'Clear area' }));
  expect(screen.queryByRole('button', { name: 'Clear area' })).not.toBeInTheDocument();
});
