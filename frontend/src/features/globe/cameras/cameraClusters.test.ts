import { act, renderHook } from '@testing-library/react';
import { useCameraSelection } from './useCameraSelection';
import type { CameraState } from './useCameras';
import type { GlobeEngineHandle } from '../useGlobeEngine';
import { expect, it, vi } from 'vitest';
import type { Camera } from '@/lib/api/cameras';
import { clusterCameras, CAMERA_MARKER_BUDGET } from './cameraClusters';
import { buildCameraLayers } from './cameraLayers';

const camera = (id: string, longitude: number, latitude: number): Camera => ({
  id,
  longitude,
  latitude,
  provider: 'tfl',
  title: id,
  snapshot_url: null,
  source_url: 'https://tfl.gov.uk/',
  attribution: 'TfL',
  captured_at: null,
  coordinate_precision: 'exact',
});

it('clusters distant cameras, unpacks on zoom and retains the selected individual', () => {
  const rows = [camera('a', 0, 0), camera('b', 0.01, 0), camera('c', 0.02, 0)];
  expect(clusterCameras(rows, 1, null).clusters[0]?.count).toBe(3);
  expect(clusterCameras(rows, 13, null).loose).toHaveLength(3);
  const selected = clusterCameras(rows, 1, 'b');
  expect(selected.loose.map((row) => row.id)).toContain('b');
  expect(selected.clusters[0]?.count).toBe(2);
  const pick = vi.fn();
  const layers = buildCameraLayers(rows, vi.fn(), 'b', false, 1, pick);
  expect(layers.map((layer) => layer.id)).toContain('selected-camera-halo');
  const props = layers.find((layer) => layer.id === 'public-camera-clusters')!.props as unknown as {
    onClick: (info: { object: unknown }) => void;
  };
  props.onClick({ object: selected.clusters[0] });
  expect(pick).toHaveBeenCalledWith(selected.clusters[0]);
});

it('bounds world-wide graphics without dropping any geographic records', () => {
  const rows = Array.from({ length: 75000 }, (_, i) =>
    camera(String(i), ((i * 137.508) % 360) - 180, ((i * 37.2) % 178) - 89),
  );
  const { loose, clusters } = clusterCameras(rows, 13, '74999');
  expect(loose.length + clusters.length).toBeLessThanOrEqual(CAMERA_MARKER_BUDGET);
  expect(loose.length + clusters.reduce((count, cell) => count + cell.count, 0)).toBe(rows.length);
  expect(loose.some((row) => row.id === '74999')).toBe(true);
  expect(clusters.some((row) => row.longitude < -100)).toBe(true);
  expect(clusters.some((row) => row.longitude > 100)).toBe(true);
});

it('keeps date-line clusters at the date line instead of Greenwich', () => {
  const { clusters } = clusterCameras([camera('a', 179.99, 20), camera('b', -179.99, 20)], 1, null);
  expect(Math.abs(clusters[0]!.longitude)).toBeCloseTo(180);
});

it('zooms cluster picks while protecting measurement gestures', () => {
  const rows = [camera('a', 0, 0), camera('b', 0.01, 0)];
  const flyTo = vi.fn();
  const engine = {
    flyTo,
    getZoom: () => 2,
    onView: () => () => undefined,
  } as unknown as GlobeEngineHandle;
  const cameras = { visible: rows, selected: null, select: vi.fn() } as unknown as CameraState;
  const { result, rerender } = renderHook(
    ({ picking }) => useCameraSelection(cameras, picking, vi.fn(), engine, 'globe'),
    { initialProps: { picking: false } },
  );
  const pick = () => {
    const layer = result.current.cameraLayers.find((item) => item.id === 'public-camera-clusters')!;
    const props = layer.props as unknown as { onClick: (info: { object: unknown }) => void };
    props.onClick({ object: { longitude: 0.005, latitude: 0, count: 2 } });
  };
  act(pick);
  expect(flyTo).toHaveBeenCalledWith({ center: [0.005, 0], zoom: 4 });
  rerender({ picking: true });
  act(pick);
  expect(flyTo).toHaveBeenCalledTimes(1);
});

it('unpacks a target viewport despite a large worldwide catalogue', () => {
  const distant = Array.from({ length: 75000 }, (_, i) =>
    camera(String(i), ((i * 137.508) % 360) - 180, 30 + (i % 50)),
  );
  const nearby = [camera('local-a', 0, 0), camera('local-b', 0.01, 0), camera('local-c', 0.02, 0)];
  const rows = [...distant, ...nearby];
  const bounds = { west: -0.1, east: 0.1, south: -0.1, north: 0.1 };
  expect(clusterCameras(rows, 1, null, bounds).clusters[0]?.count).toBe(3);
  const detail = clusterCameras(rows, 13, null, bounds);
  expect(detail.clusters).toHaveLength(0);
  expect(detail.loose.map((row) => row.id)).toEqual(['local-a', 'local-b', 'local-c']);
});

it('culls across wrapped viewport bounds without losing date-line cameras', () => {
  const rows = [camera('east', 179, 0), camera('west', -179, 0), camera('outside', 0, 0)];
  const view = clusterCameras(rows, 13, null, { west: 170, east: -170, south: -10, north: 10 });
  expect(view.loose.map((row) => row.id)).toEqual(['east', 'west']);
});
