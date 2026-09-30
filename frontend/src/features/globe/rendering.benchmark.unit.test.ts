import { expect, it, vi } from 'vitest';
import type { Camera } from '@/lib/api/cameras';
import { liveEvent } from '@/test/fixtures';
import { buildEventLayers } from './layers/registry';
import { clusterCameras, CAMERA_MARKER_BUDGET } from './cameras/cameraClusters';

it('measures realistic bounded event and large camera layer construction', () => {
  const cameras: Camera[] = Array.from({ length: 75000 }, (_, i) => ({
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
  }));
  const events = Array.from({ length: 5000 }, (_, i) =>
    liveEvent({
      id: String(i),
      category: i % 2 ? 'aviation' : 'disaster',
      point: { lon: ((i * 137.508) % 360) - 180, lat: ((i * 37.2) % 178) - 89 },
    }),
  );
  const times = (run: () => void) =>
    Array.from({ length: 5 }, () => {
      const start = performance.now();
      run();
      return Number((performance.now() - start).toFixed(2));
    });
  const eventMs = times(() => {
    expect(
      buildEventLayers(events, [], vi.fn(), null, { zoom: 1.5, onCluster: vi.fn() }).length,
    ).toBeGreaterThan(0);
  });
  const cameraMs = times(() => {
    const result = clusterCameras(cameras, 13, null);
    expect(result.loose.length + result.clusters.length).toBeLessThanOrEqual(CAMERA_MARKER_BUDGET);
    expect(result.loose.length + result.clusters.reduce((total, row) => total + row.count, 0)).toBe(
      75000,
    );
  });
  // Timings are audit evidence, deliberately not machine-dependent pass thresholds.
  process.stdout.write(JSON.stringify({ eventMs, cameraMs }) + '\n');
});
