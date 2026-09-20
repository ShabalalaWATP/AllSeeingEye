import { ScatterplotLayer } from '@deck.gl/layers';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { createMapLibreEngine } from './MapLibreEngine';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
beforeEach(() => {
  FakeMap.reset();
  MapboxOverlay.reset();
  vi.useFakeTimers();
});
afterEach(() => vi.useRealTimers());

it('restores only the latest layers after base context recovery and ignores duplicate restores', () => {
  const status = vi.fn();
  const engine = createMapLibreEngine({ onRenderStatus: status });
  engine.mount(document.createElement('div'));
  const map = FakeMap.instances[0]!;
  map.fire('style.load');
  const first = MapboxOverlay.instances[0]!;
  map.fire('webglcontextlost');
  expect(first.finalize).toHaveBeenCalledOnce();
  engine.setLayers([new ScatterplotLayer({ id: 'old' })]);
  engine.setLayers([new ScatterplotLayer({ id: 'latest' })]);
  engine.setProjection('mercator');
  engine.setBaseLayer('streets');
  expect(map.setStyle).not.toHaveBeenCalled();
  expect(first.setProps).not.toHaveBeenCalled();
  map.fire('webglcontextrestored');
  map.fire('style.load');
  expect(map.setStyle).toHaveBeenCalledOnce();
  map.fire('webglcontextrestored');
  expect(MapboxOverlay.instances).toHaveLength(2);
  expect(MapboxOverlay.instances[1]!.props.layers).toEqual([
    expect.objectContaining({ id: 'latest' }),
  ]);
  expect(map.setProjection).toHaveBeenLastCalledWith({ type: 'mercator' });
  expect(status).toHaveBeenLastCalledWith('ready', '');
  engine.destroy();
  expect(MapboxOverlay.instances[1]!.finalize).toHaveBeenCalledOnce();
  expect(vi.getTimerCount()).toBe(0);
});

it('bounds independent overlay recovery attempts and never recreates after destroy', () => {
  const status = vi.fn();
  const engine = createMapLibreEngine({ onRenderStatus: status });
  engine.mount(document.createElement('div'));
  for (let i = 0; i < 3; i++) {
    const overlay = MapboxOverlay.instances.at(-1)!;
    overlay.canvas.dispatchEvent(new Event('webglcontextlost', { cancelable: true }));
    vi.runOnlyPendingTimers();
  }
  expect(MapboxOverlay.instances).toHaveLength(3);
  expect(status).toHaveBeenLastCalledWith('failed', expect.stringContaining('Reload'));
  engine.setLayers([new ScatterplotLayer({ id: 'ignored-after-failure' })]);
  engine.destroy();
  vi.runAllTimers();
  expect(MapboxOverlay.instances).toHaveLength(3);
});

it('cancels pending recovery on unmount and invalidates an export on graphics loss', async () => {
  const engine = createMapLibreEngine({ captureEnabled: true });
  engine.mount(document.createElement('div'));
  MapboxOverlay.instances[0]!.canvas.dispatchEvent(new Event('webglcontextlost'));
  await expect(engine.captureImage(new AbortController().signal)).rejects.toThrow('unavailable');
  engine.destroy();
  vi.runAllTimers();
  expect(MapboxOverlay.instances).toHaveLength(1);
});

it('reports a base context that cannot recover without retry loops', () => {
  const status = vi.fn();
  const engine = createMapLibreEngine({ onRenderStatus: status });
  engine.mount(document.createElement('div'));
  FakeMap.instances[0]!.fire('webglcontextlost');
  vi.advanceTimersByTime(10_000);
  expect(status).toHaveBeenLastCalledWith('failed', expect.stringContaining('did not recover'));
  expect(MapboxOverlay.instances).toHaveLength(1);
  engine.destroy();
});

it('contains a picking failure instead of throwing through the map click handler', () => {
  const status = vi.fn();
  const engine = createMapLibreEngine({ onRenderStatus: status });
  engine.mount(document.createElement('div'));
  MapboxOverlay.instances[0]!.pickMultipleObjects.mockImplementation(() => {
    throw new Error('GPU unavailable');
  });
  expect(engine.pickObjectsAt?.(10, 20)).toEqual([]);
  expect(status).toHaveBeenLastCalledWith('failed', expect.stringContaining('Reload'));
  engine.destroy();
});

it('ignores callbacks from a failed overlay before and after its replacement is ready', () => {
  const status = vi.fn();
  const engine = createMapLibreEngine({ onRenderStatus: status });
  engine.mount(document.createElement('div'));
  const stale = MapboxOverlay.instances[0]!;
  stale.canvas.dispatchEvent(new Event('webglcontextlost'));
  (stale.props.onError as () => void)();
  vi.advanceTimersByTime(250);
  expect(MapboxOverlay.instances).toHaveLength(2);
  const replacement = MapboxOverlay.instances[1]!;
  status.mockClear();
  replacement.getCanvas.mockClear();
  (stale.props.onError as () => void)();
  (stale.props.onLoad as () => void)();
  vi.runOnlyPendingTimers();
  expect(replacement.finalize).not.toHaveBeenCalled();
  expect(replacement.getCanvas).not.toHaveBeenCalled();
  expect(status).not.toHaveBeenCalled();
  engine.setLayers([new ScatterplotLayer({ id: 'still-visible' })]);
  expect(replacement.setProps).toHaveBeenCalledWith({
    layers: [expect.objectContaining({ id: 'still-visible' })],
  });
  engine.destroy();
});
