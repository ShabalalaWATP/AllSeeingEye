import { act, fireEvent, render, renderHook, screen } from '@testing-library/react';
import { Children, type ReactElement } from 'react';
import { expect, it, vi } from 'vitest';
import type { GlobeEngineHandle } from './useGlobeEngine';
import { useMapWorkspaceTools } from './useMapWorkspaceTools';
import { mapPlanningPanels } from './MapPlanningPanels';
import type { NavigationRoute } from '@/lib/api/navigation';
import type { PanelProps } from './mapToolDefinitions';

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
it('routes corridor research around the calculated route rather than an older saved path', () => {
  const { result } = renderHook(() => useMapWorkspaceTools(engine, true, 'map'));
  act(() =>
    result.current.drawing.load('path', [
      [0, 0],
      [0.1, 0.1],
    ]),
  );
  act(() => result.current.drawingWorkspace.addSketch());
  const path = result.current.drawingWorkspace.selected!;
  act(() => result.current.drawingWorkspace.updateObject(path.id, { name: 'Earlier survey' }));
  act(() =>
    result.current.setRoute({
      coordinates: [
        [-0.12, 51.5],
        [-0.15, 51.6],
      ],
    } as NavigationRoute),
  );
  const panels: ReactElement<PanelProps>[] = mapPlanningPanels(result.current);
  const routePanel = panels.find((panel) => panel.props.label === 'Route planner')!;
  const corridor = Children.toArray(routePanel.props.children)[1] as ReactElement;
  render(corridor);
  expect(screen.getByRole('combobox', { name: 'Corridor path source' })).toHaveValue('route');
  fireEvent.click(screen.getByRole('button', { name: 'Preview corridor for research' }));
  const ring = result.current.research.area?.features[0]?.geometry;
  expect(ring?.type).toBe('Polygon');
  if (ring?.type !== 'Polygon') throw new Error('Expected a corridor polygon');
  expect(ring.coordinates[0]?.every(([, latitude]) => latitude > 51 && latitude < 52)).toBe(true);
  expect(screen.getByRole('option', { name: 'Drawing: Earlier survey' })).toBeInTheDocument();
});
