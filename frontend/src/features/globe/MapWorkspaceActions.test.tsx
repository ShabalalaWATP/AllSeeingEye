import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { useEffect } from 'react';
import { useAuthStore } from '@/stores/auth';
import { plainUser } from '@/test/fixtures';
import { researchAreaGeometry } from '@/lib/map/researchAreaGeometry';
import { MapToolActivity } from './MapToolActivity';
import { MapWorkspacePanel } from './MapWorkspacePanel';
import { useMapWorkspaceTools } from './useMapWorkspaceTools';
import type { GlobeEngineHandle } from './useGlobeEngine';

const engine: GlobeEngineHandle = {
  setLayers: vi.fn(),
  flyTo: vi.fn(),
  getZoom: () => 4,
  spin: vi.fn(),
  onCursor: () => () => undefined,
  onView: () => () => undefined,
  onClick: () => () => undefined,
  onDrag: () => () => undefined,
  setSketchMode: vi.fn(),
};
let tools: ReturnType<typeof useMapWorkspaceTools>;
const open = vi.fn();
function Workspace() {
  const current = useMapWorkspaceTools(engine, true, 'map');
  useEffect(() => {
    tools = current;
  }, [current]);
  return (
    <>
      <MapWorkspacePanel tools={current} open={open} />
      <MapToolActivity tools={current} />
    </>
  );
}
beforeEach(() => useAuthStore.setState({ user: plainUser, status: 'authenticated' }));

it('manages named point visibility, locking and radio handoff through the object list', () => {
  render(<Workspace />);
  expect(screen.getByText('Your map has no drawings or analysis results yet.')).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Draw or open a collection' }));
  expect(open).toHaveBeenLastCalledWith('Draw on map');
  act(() => tools.drawingWorkspace.addPoint([1, 52]));
  const id = tools.drawingWorkspace.objects[0]!.id;
  act(() => tools.drawingWorkspace.updateObject(id, { name: 'Hill site' }));
  fireEvent.click(screen.getByRole('checkbox', { name: 'Hill site' }));
  expect(tools.drawingWorkspace.objects[0]!.visible).toBe(false);
  fireEvent.click(screen.getByRole('button', { name: 'Edit' }));
  expect(tools.drawingWorkspace.selectedId).toBe(id);
  fireEvent.click(screen.getByRole('button', { name: 'Use as transmitter' }));
  expect(tools.rf.origin).toEqual([1, 52]);
  expect(tools.rf.siteNames.origin).toBe('Hill site');
  expect(open).toHaveBeenLastCalledWith('RF link calculator');
  act(() => tools.drawingWorkspace.updateObject(id, { locked: true }));
  expect(screen.getByRole('button', { name: 'Remove' })).toBeDisabled();
  expect(screen.getByText('Hill site · locked')).toBeVisible();
  act(() => tools.drawingWorkspace.updateObject(id, { locked: false }));
  fireEvent.click(screen.getByRole('button', { name: 'Remove' }));
  expect(tools.drawingWorkspace.objects).toEqual([]);
  expect(tools.rf.origin).toEqual([1, 52]);
});

it('hides workspace overlays without deleting their geometry and clears them explicitly', () => {
  render(<Workspace />);
  act(() => {
    tools.measurement.add(1, 1);
    tools.drawing.load('path', [
      [1, 1],
      [2, 2],
    ]);
    tools.adoptResearch(
      researchAreaGeometry('rectangle', [
        [0, 0],
        [2, 2],
      ]),
    );
    tools.rf.setSite('origin', [1, 1]);
    tools.rf.setProfilePoint([1.1, 1.1]);
    tools.setRoute({
      mode: 'walking',
      distance_km: 1,
      duration_seconds: 600,
      coordinates: [
        [1, 1],
        [1.01, 1.01],
      ],
      steps: [],
      provider: 'FOSSGIS Valhalla',
      attribution: 'Test data',
      limitations: 'Synthetic route',
    });
  });
  expect(tools.layers.some((layer) => layer.id === 'radio-profile-inspection')).toBe(true);
  for (const name of [
    'Measurement',
    'Current sketch',
    'Research boundary',
    'Radio study',
    'Planned route',
  ])
    fireEvent.click(screen.getByRole('checkbox', { name }));
  expect(tools.layers).toEqual([]);
  expect(tools.measurement.points).toEqual([[1, 1]]);
  expect(tools.research.area).not.toBeNull();
  expect(tools.rf.origin).toEqual([1, 1]);
  expect(tools.routePlanner.route).not.toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Open planned route' }));
  expect(open).toHaveBeenLastCalledWith('Route planner');
  for (const name of [
    'measurement',
    'current sketch',
    'research boundary',
    'radio study',
    'planned route',
  ])
    fireEvent.click(screen.getByRole('button', { name: `Clear ${name}` }));
  expect(screen.getByText('Your map has no drawings or analysis results yet.')).toBeVisible();
  expect(tools.rf.profilePoint).toBeNull();
});

it('leaves the existing research boundary intact when a crossing circle cannot be adopted', () => {
  render(<Workspace />);
  const area = researchAreaGeometry('rectangle', [
    [0, 0],
    [1, 1],
  ]);
  act(() => tools.adoptResearch(area));
  act(() =>
    tools.drawing.load('circle', [
      [179.9, 0],
      [-179.9, 0],
    ]),
  );
  act(() => tools.drawingWorkspace.addSketch());
  fireEvent.click(screen.getByRole('button', { name: 'Research' }));
  expect(screen.getByRole('alert')).toHaveTextContent(/cross|180|date/i);
  expect(tools.research.area).toEqual(area);
  expect(open).not.toHaveBeenCalled();
});

it('keeps drawing history and cancellation actions usable outside the inspector', () => {
  render(<Workspace />);
  act(() => tools.research.drawing.setPicking(true));
  act(() => tools.research.drawing.add(0, 0));
  act(() => tools.research.drawing.add(1, 1));
  const activity = screen.getByRole('region', { name: 'Active map tool' });
  expect(within(activity).getByRole('status')).toHaveTextContent('Research boundary');
  fireEvent.click(within(activity).getByRole('button', { name: 'Undo' }));
  expect(tools.research.drawing.anchors).toHaveLength(1);
  fireEvent.click(within(activity).getByRole('button', { name: 'Redo' }));
  expect(tools.research.drawing.anchors).toHaveLength(2);
  fireEvent.click(within(activity).getByRole('button', { name: 'Finish drawing' }));
  expect(tools.picking).toBe(false);
  act(() => tools.drawing.setPicking(true));
  act(() => tools.drawing.add(5, 5));
  fireEvent.click(screen.getByRole('button', { name: 'Discard sketch' }));
  expect(tools.drawing.anchors).toEqual([]);
});

it.each(['origin', 'receiver'] as const)(
  'shows and cancels click and drag placement for %s',
  (kind) => {
    render(<Workspace />);
    act(() => tools.rf.setPicking(kind));
    expect(screen.getByRole('status')).toHaveTextContent(
      `Choose the ${kind === 'origin' ? 'transmitter' : 'receiver'}`,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Cancel placement' }));
    expect(tools.picking).toBe(false);
    act(() => tools.rf.setSite(kind, [1, 1]));
    act(() => tools.rf.setDragSite(kind));
    expect(screen.getByRole('status')).toHaveTextContent('Drag the marked');
    fireEvent.click(screen.getByRole('button', { name: 'Cancel placement' }));
    expect(tools.rf[kind]).toEqual([1, 1]);
  },
);
