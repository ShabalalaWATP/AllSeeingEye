import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeMap } from '@/test/fakeMap';
import { createMapLibreEngine } from './MapLibreEngine';
import { captureMapImage } from './mapCapture';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/mapbox', () => import('@/test/fakeDeck'));
vi.mock('./mapCapture', () => ({ captureMapImage: vi.fn() }));

beforeEach(() => {
  FakeMap.reset();
  MapboxOverlay.reset();
  vi.mocked(captureMapImage).mockReset();
});

describe('dedicated map export engine', () => {
  it('preserves drawing buffers only for non-interactive bounded export instances', async () => {
    const ordinary = createMapLibreEngine();
    ordinary.mount(document.createElement('div'));
    expect(FakeMap.instances[0]!.options.canvasContextAttributes).toBeUndefined();
    await expect(ordinary.captureImage(new AbortController().signal)).rejects.toThrow(
      'unavailable',
    );
    const exporting = createMapLibreEngine({ captureEnabled: true });
    exporting.mount(document.createElement('div'));
    expect(FakeMap.instances[1]!.options).toMatchObject({
      interactive: false,
      pixelRatio: 1,
      canvasContextAttributes: { preserveDrawingBuffer: true },
    });
    expect(MapboxOverlay.instances[1]!.props.useDevicePixels).toBe(1);
  });

  it('aborts pending capture on destroy and rejects concurrent capture', async () => {
    vi.mocked(captureMapImage).mockImplementation(
      (_map, _overlay, signal) =>
        new Promise((_resolve, reject) => {
          signal.addEventListener('abort', () =>
            reject(new DOMException('cancelled', 'AbortError')),
          );
        }),
    );
    const engine = createMapLibreEngine({ captureEnabled: true });
    engine.mount(document.createElement('div'));
    const pending = engine.captureImage(new AbortController().signal);
    await expect(engine.captureImage(new AbortController().signal)).rejects.toThrow(
      'already running',
    );
    engine.destroy();
    await expect(pending).rejects.toMatchObject({ name: 'AbortError' });
  });

  it.each(['camera', 'layers', 'projection', 'basemap', 'lite', 'resize'])(
    'invalidates captured state after a %s change',
    async (change) => {
      vi.mocked(captureMapImage).mockResolvedValue(new Blob(['png']));
      const engine = createMapLibreEngine({ captureEnabled: true });
      engine.mount(document.createElement('div'));
      await engine.captureImage(new AbortController().signal);
      const unchanged = vi.mocked(captureMapImage).mock.calls[0]![3];
      expect(unchanged()).toBe(true);
      if (change === 'camera')
        engine.restoreCamera({ center: [1, 2], zoom: 3, pitch: 0, bearing: 0 });
      if (change === 'layers') engine.setLayers([]);
      if (change === 'projection') engine.setProjection('mercator');
      if (change === 'basemap') engine.setBaseLayer('dark');
      if (change === 'lite') engine.setLite(true);
      if (change === 'resize') FakeMap.instances[0]!.fire('resize');
      expect(unchanged()).toBe(false);
    },
  );

  it('refuses an export whose basemap or observation renderer previously failed', async () => {
    const engine = createMapLibreEngine({ captureEnabled: true });
    engine.mount(document.createElement('div'));
    FakeMap.instances[0]!.fire('error');
    await expect(engine.captureImage(new AbortController().signal)).rejects.toThrow('fresh export');
    expect(captureMapImage).not.toHaveBeenCalled();
  });
});
