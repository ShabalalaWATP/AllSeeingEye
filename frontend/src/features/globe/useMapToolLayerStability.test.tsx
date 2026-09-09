import { act, renderHook } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import type { NavigationRoute } from '@/lib/api/navigation';
import type { SketchDrag, SketchDragHandler } from '@/lib/map/MapEngine';
import type { Position } from '@/lib/map/geoJsonTypes';
import { rfMapEstimate } from '@/lib/map/rfMap';
import { DEFAULT_RF_INPUTS } from '@/lib/map/rfPlanning';
import type { ViewMode } from '@/stores/globe';
import type { GlobeEngineHandle } from './useGlobeEngine';
import { useMapWorkspaceTools } from './useMapWorkspaceTools';

it('keeps unchanged tool geometry stable during drawing previews and refreshes only affected inputs', () => {
  const handlers = new Set<SketchDragHandler>();
  const engine: GlobeEngineHandle = {
    setLayers: vi.fn(),
    flyTo: vi.fn(),
    getZoom: () => 10,
    spin: vi.fn(),
    onClick: () => () => undefined,
    onCursor: () => () => undefined,
    onView: () => () => undefined,
    setSketchMode: vi.fn(),
    onDrag: (handler) => {
      handlers.add(handler);
      return () => {
        handlers.delete(handler);
      };
    },
  };
  const route: NavigationRoute = {
    mode: 'driving',
    distance_km: 200,
    duration_seconds: 7200,
    coordinates: Array.from({ length: 20_000 }, (_, i): Position => [-1 + i / 10_000, 51]),
    steps: [{ instruction: 'Continue', distance_km: 200, duration_seconds: 7200 }],
    provider: 'FOSSGIS Valhalla',
    attribution: 'OpenStreetMap',
    limitations: 'Test fixture.',
  };
  const { result, rerender, unmount } = renderHook(
    ({ mode }: { mode: ViewMode }) => useMapWorkspaceTools(engine, true, mode),
    { initialProps: { mode: 'map' } },
  );
  const layer = (id: string) => {
    const found = result.current.layers.find((candidate) => candidate.id === id);
    if (!found) throw new Error(`Missing layer: ${id}`);
    return found;
  };
  const emit = (phase: SketchDrag['phase'], current: Position) =>
    act(() => {
      for (const handler of handlers)
        handler({
          phase,
          start: { lon: 0, lat: 51 },
          current: { lon: current[0], lat: current[1] },
        });
    });
  act(() => {
    result.current.setRoute(route);
    result.current.rf.setEstimate(rfMapEstimate(DEFAULT_RF_INPUTS, [0, 51], [0.1, 51]));
    result.current.measurement.add(0, 51);
    result.current.measurement.add(0.2, 51);
    result.current.drawing.setShape('rectangle');
  });
  act(() => result.current.drawing.setPicking(true));
  const unchangedIds = ['navigation-route', 'rf-estimate-paths', 'measurement-path'];
  const before = unchangedIds.map(layer);
  expect(route.coordinates).toHaveLength(20_000);
  emit('start', [0, 51]);
  emit('move', [0.1, 51.1]);
  const firstPreview = layer('drawing-measurement-path');
  emit('move', [0.2, 51.2]);
  expect(layer('drawing-measurement-path')).not.toBe(firstPreview);
  expect(layer('drawing-measurement-path').props.data).not.toBe(firstPreview.props.data);
  unchangedIds.forEach((id, index) => {
    expect(layer(id), `${id} should retain its layer`).toBe(before[index]);
    expect(layer(id).props.data, `${id} should retain its geometry`).toBe(
      before[index]?.props.data,
    );
  });
  emit('end', [0.2, 51.2]);
  unchangedIds.forEach((id, index) => expect(layer(id)).toBe(before[index]));

  rerender({ mode: 'globe' });
  unchangedIds.forEach((id, index) => {
    expect(layer(id), `${id} should react to projection`).not.toBe(before[index]);
    expect(layer(id).props.data).not.toBe(before[index]?.props.data);
  });
  expect(layer('navigation-route').props.wrapLongitude).toBe(false);
  const globeRoute = layer('navigation-route');
  const globeRf = layer('rf-estimate-paths');
  const globeMeasurement = layer('measurement-path');
  const globeDrawing = layer('drawing-measurement-path');
  const replacement: NavigationRoute = {
    ...route,
    coordinates: [
      [10, 50],
      [11, 51],
    ],
  };
  act(() => result.current.setRoute(replacement));
  expect(layer('navigation-route')).not.toBe(globeRoute);
  expect(layer('navigation-route').props.data).not.toBe(globeRoute.props.data);
  expect(layer('rf-estimate-paths')).toBe(globeRf);
  expect(layer('measurement-path')).toBe(globeMeasurement);
  expect(layer('drawing-measurement-path')).toBe(globeDrawing);
  unmount();
  expect(handlers.size).toBe(0);
});
