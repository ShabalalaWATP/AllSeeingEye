import { act, fireEvent, render, renderHook, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser } from '@/test/fixtures';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { researchAreaGeometry } from '@/lib/map/researchAreaGeometry';
import { parseLocalGeoJson } from '@/lib/map/localGeoJson';
import type { Position } from '@/lib/map/geoJsonTypes';
import type { GlobeEngineHandle } from './useGlobeEngine';
import { useMapWorkspaceTools } from './useMapWorkspaceTools';
import { MapWorkspacePanel } from './MapWorkspacePanel';
import { MapToolActivity } from './MapToolActivity';

const engine: GlobeEngineHandle = {
  setLayers: vi.fn(),
  flyTo: vi.fn(),
  getZoom: () => 4,
  spin: vi.fn(),
  onCursor: () => () => undefined,
  onView: () => () => undefined,
  onClick: () => () => undefined,
  setSketchMode: vi.fn(),
};
const anchors: Position[] = [
  [0, 0],
  [2, 0],
  [2, 2],
  [0, 2],
];
beforeEach(() => {
  useAuthStore.setState({ user: plainUser, status: 'authenticated' });
});

it('uses the selected saved drawing as the exact research boundary without changing the drawing', () => {
  const { result } = renderHook(() => useMapWorkspaceTools(engine, true, 'map'));
  act(() => result.current.drawing.load('polygon', anchors));
  act(() => result.current.drawingWorkspace.addSketch());
  const drawing = result.current.drawingWorkspace.objects[0]!;
  const open = vi.fn();
  render(<MapWorkspacePanel tools={result.current} open={open} />);
  fireEvent.click(screen.getByRole('button', { name: 'Research' }));
  expect(open).toHaveBeenCalledWith('Research area');
  expect(result.current.research.area).toEqual(researchAreaGeometry('polygon', anchors));
  expect(result.current.drawingWorkspace.objects[0]).toEqual(drawing);
  act(() => result.current.activatePanel('RF link calculator'));
  expect(result.current.research.area).not.toBeNull();
});

it('adopts polygon holes independently and hands off exclusive map input ownership', () => {
  const { result } = renderHook(() => useMapWorkspaceTools(engine, true, 'globe'));
  const area = parseLocalGeoJson(
    JSON.stringify({
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: { label: 'Area with an exclusion' },
          geometry: {
            type: 'Polygon',
            coordinates: [
              [
                [0, 0],
                [4, 0],
                [4, 4],
                [0, 4],
                [0, 0],
              ],
              [
                [1, 1],
                [1, 2],
                [2, 2],
                [2, 1],
                [1, 1],
              ],
            ],
          },
        },
      ],
    }),
  ).canonical;
  act(() => result.current.rf.setPicking('origin'));
  act(() => result.current.adoptResearch(area));
  expect(result.current.picking).toBe(false);
  expect(result.current.research.area).toEqual(area);
  expect(result.current.research.area).not.toBe(area);
  act(() => result.current.setVisible('research', false));
  expect(result.current.layers.some((layer) => layer.id === 'research-area-imported')).toBe(false);
  expect(result.current.research.area).toEqual(area);
  act(() => result.current.research.drawing.setPicking(true));
  expect(result.current.research.imported).toBeNull();
});

it('rejects non-area adoption and retains the previous boundary', () => {
  const { result } = renderHook(() => useMapWorkspaceTools(engine, true, 'map'));
  const area = researchAreaGeometry('polygon', anchors);
  act(() => result.current.adoptResearch(area));
  const point = parseLocalGeoJson(
    JSON.stringify({
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: {},
          geometry: { type: 'Point', coordinates: [0, 0] },
        },
      ],
    }),
  ).canonical;
  expect(() => act(() => result.current.adoptResearch(point))).toThrow('Choose an area');
  expect(result.current.research.area).toEqual(area);
});

it.each(['access', 'account', 'role', 'inactive', 'status'] as const)(
  'clears adopted geometry and collection after %s changes',
  (change) => {
    const { result } = renderHook(() => useMapWorkspaceTools(engine, true, 'map'));
    act(() => result.current.drawing.load('polygon', anchors));
    act(() => result.current.drawingWorkspace.addSketch());
    act(() => result.current.adoptResearch(researchAreaGeometry('polygon', anchors)));
    act(() => result.current.setVisible('research', false));
    act(() => result.current.measurement.add(1, 1));
    act(() => {
      if (change === 'access') invalidateWorkspaceAccess();
      else if (change === 'account') useAuthStore.setState({ user: adminUser });
      else if (change === 'role') useAuthStore.setState({ user: { ...plainUser, role: 'admin' } });
      else if (change === 'inactive')
        useAuthStore.setState({ user: { ...plainUser, is_active: false } });
      else useAuthStore.setState({ status: 'anonymous', user: null });
    });
    expect(result.current.research.area).toBeNull();
    expect(result.current.drawingWorkspace.objects).toEqual([]);
    expect(result.current.visible.research).toBe(true);
    expect(result.current.measurement.points).toEqual([]);
  },
);

it('hands map dragging exclusively to a radio site and retains visible sites without a result', () => {
  const dragEngine = { ...engine, onDrag: () => () => undefined };
  const { result } = renderHook(() => useMapWorkspaceTools(dragEngine, true, 'map'));
  act(() => result.current.rf.setSite('origin', [1, 1], 'Test site'));
  expect(result.current.layers.some((layer) => layer.id === 'radio-workspace-sites')).toBe(true);
  act(() => result.current.drawing.setPicking(true));
  act(() => result.current.rf.setDragSite('origin'));
  expect(result.current.drawing.picking).toBe(false);
  expect(result.current.rf.interaction).toBe('drag');
  expect(engine.setSketchMode).toHaveBeenLastCalledWith('drag');
  act(() => result.current.measurement.setPicking(true));
  expect(result.current.rf.picking).toBeNull();
  expect(engine.setSketchMode).toHaveBeenLastCalledWith('points');
});

it('exposes measurement actions outside the inspector and releases input when it closes', () => {
  const { result } = renderHook(() => useMapWorkspaceTools(engine, true, 'map'));
  act(() => result.current.measurement.add(1, 1));
  act(() => result.current.measurement.setPicking(true));
  const view = render(<MapToolActivity tools={result.current} />);
  fireEvent.click(screen.getByRole('button', { name: 'Undo point' }));
  expect(result.current.measurement.points).toEqual([]);
  fireEvent.click(screen.getByRole('button', { name: 'Finish measuring' }));
  expect(result.current.picking).toBe(false);
  act(() => result.current.measurement.setPicking(true));
  act(() => result.current.activatePanel(null));
  expect(result.current.picking).toBe(false);
  view.rerender(<MapToolActivity tools={result.current} />);
  expect(screen.queryByRole('region', { name: 'Active map tool' })).not.toBeInTheDocument();
});
