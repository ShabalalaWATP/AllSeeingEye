import { act, renderHook } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import type { Camera } from '@/lib/api/cameras';
import * as clustering from './cameraClusters';
import { cameraVectors } from './cameraVectors';
import { useCameraSelection } from './useCameraSelection';
import type { CameraState } from './useCameras';
import type { GlobeEngineHandle } from '../useGlobeEngine';
import type { ViewHandler } from '../useGlobeEngine';

const camera = (i: number): Camera => ({
  id: String(i),
  longitude: ((i * 137.508) % 360) - 180,
  latitude: ((i * 37.2) % 178) - 89,
  provider: 'tfl',
  title: String(i),
  snapshot_url: null,
  source_url: 'https://tfl.gov.uk/',
  attribution: 'TfL',
  captured_at: null,
  coordinate_precision: 'exact',
});

it('rejects overfull resolutions early while retaining all75000 cameras', () => {
  const rows = Array.from({ length: 75000 }, (_, i) => camera(i));
  const round = vi.spyOn(Math, 'round');
  const result = clustering.clusterCameras(rows, 13, '74999');
  const quantisations = round.mock.calls.length;
  round.mockRestore();
  expect(result.loose.length + result.clusters.length).toBeLessThanOrEqual(2000);
  expect(result.loose.length + result.clusters.reduce((sum, cell) => sum + cell.count, 0)).toBe(
    75000,
  );
  expect(result.loose.some((item) => item.id === '74999')).toBe(true);
  // Former implementation performed around3 million coordinate quantisations.
  // Bound actual work rather than asserting hardware-dependent milliseconds.
  expect(quantisations).toBeLessThan(500000);
});

it('reuses immutable catalogue vectors and rebuilds them after catalogue replacement', () => {
  const rows = [camera(0)];
  expect(cameraVectors(rows)).toBe(cameraVectors(rows));
  const next = [{ ...rows[0]!, longitude: 0 }];
  expect(cameraVectors(next)).not.toBe(cameraVectors(rows));
  expect(cameraVectors(next)[0]).not.toBe(cameraVectors(rows)[0]);
});

it('reuses camera grouping across gesture/projection changes and skips disabled movement listeners', () => {
  const build = vi.spyOn(clustering, 'clusterCameras');
  const engine = {
    onView: vi.fn(() => vi.fn()),
    flyTo: vi.fn(),
    getZoom: () => 2,
  } as unknown as GlobeEngineHandle;
  const rows = [camera(0), camera(1)];
  const state = {
    visible: rows,
    selected: null,
    select: vi.fn(),
    enabled: false,
  } as unknown as CameraState;
  const { rerender } = renderHook(
    ({ picking, mode }: { picking: boolean; mode: 'globe' | 'map' }) =>
      useCameraSelection(state, picking, vi.fn(), engine, mode),
    { initialProps: { picking: false, mode: 'globe' as 'globe' | 'map' } },
  );
  expect(build).toHaveBeenCalledOnce();
  rerender({ picking: true, mode: 'globe' });
  rerender({ picking: false, mode: 'map' });
  expect(build).toHaveBeenCalledOnce();
  expect(engine.onView).not.toHaveBeenCalled();
});

it('clusters once after dragging settles and ignores an unchanged viewport', () => {
  vi.useFakeTimers();
  try {
    let move: ViewHandler = () => undefined;
    const build = vi.spyOn(clustering, 'clusterCameras');
    const engine = {
      onView: (handler: ViewHandler) => {
        move = handler;
        return vi.fn();
      },
      getZoom: () => 13,
      flyTo: vi.fn(),
      getViewportBounds: () => ({ west: -1, east: 1, south: -1, north: 1 }),
    } as unknown as GlobeEngineHandle;
    const state = {
      visible: [camera(0)],
      selected: null,
      select: vi.fn(),
      enabled: true,
    } as unknown as CameraState;
    const { unmount } = renderHook(() => useCameraSelection(state, false, vi.fn(), engine, 'map'));
    expect(build).toHaveBeenCalledOnce();
    act(() => {
      for (let i = 0; i < 20; i++) {
        move({ zoom: 13 });
        vi.advanceTimersByTime(100);
      }
    });
    expect(build).toHaveBeenCalledOnce();
    act(() => {
      vi.advanceTimersByTime(150);
    });
    expect(build).toHaveBeenCalledTimes(2);
    act(() => {
      move({ zoom: 13 });
      vi.advanceTimersByTime(150);
    });
    expect(build).toHaveBeenCalledTimes(2);
    unmount();
  } finally {
    vi.useRealTimers();
  }
});
