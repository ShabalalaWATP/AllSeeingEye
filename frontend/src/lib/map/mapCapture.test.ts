import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Map as MapLibreMap } from 'maplibre-gl';
import type { MapboxOverlay } from '@deck.gl/mapbox';
import { captureMapImage, CAPTURE_TIMEOUT_MS, compositeMapCanvases } from './mapCapture';

function fixture() {
  const base = document.createElement('canvas');
  const deck = document.createElement('canvas');
  base.width = deck.width = 100;
  base.height = deck.height = 100;
  const handlers = new Map<string, Set<() => void>>();
  const map = {
    getCanvas: () => base,
    loaded: vi.fn(() => true),
    areTilesLoaded: vi.fn(() => true),
    triggerRepaint: vi.fn(),
    on: (name: string, fn: () => void) => {
      if (!handlers.has(name)) handlers.set(name, new Set());
      handlers.get(name)!.add(fn);
    },
    off: (name: string, fn: () => void) => handlers.get(name)?.delete(fn),
  };
  let afterRender: () => void = () => undefined;
  const overlay = {
    getCanvas: () => deck,
    setProps: vi.fn((props: { onAfterRender?: () => void }) => {
      if (props.onAfterRender) afterRender = props.onAfterRender;
    }),
  };
  const controller = new AbortController();
  const unchanged = vi.fn(() => true);
  const layersLoaded = vi.fn(() => true);
  return {
    base,
    deck,
    map,
    overlay,
    controller,
    unchanged,
    layersLoaded,
    handlers,
    fire: (name: string) => handlers.get(name)?.forEach((fn) => fn()),
    frame: () => afterRender(),
    capture: () =>
      captureMapImage(
        map as unknown as MapLibreMap,
        overlay as unknown as MapboxOverlay,
        controller.signal,
        unchanged,
        layersLoaded,
      ),
  };
}

const context = {
  drawImage: vi.fn(),
  getImageData: vi.fn(() => ({ data: new Uint8ClampedArray([0, 0, 0, 255, 10, 20, 30, 255]) })),
};

beforeEach(() => {
  vi.useFakeTimers();
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(
    context as unknown as CanvasRenderingContext2D,
  );
  vi.spyOn(HTMLCanvasElement.prototype, 'toBlob').mockImplementation((done) =>
    done(new Blob(['png'], { type: 'image/png' })),
  );
  context.drawImage.mockClear();
  context.getImageData
    .mockReset()
    .mockReturnValue({ data: new Uint8ClampedArray([0, 0, 0, 255, 10, 20, 30, 255]) });
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe('actual map image capture', () => {
  it('waits for map idle and a loaded observation frame, then composes in order', async () => {
    const f = fixture();
    const result = f.capture();
    f.frame();
    expect(context.drawImage).not.toHaveBeenCalled();
    f.layersLoaded.mockReturnValue(false);
    f.fire('idle');
    f.frame();
    expect(context.drawImage).not.toHaveBeenCalled();
    f.layersLoaded.mockReturnValue(true);
    f.frame();
    expect((await result).type).toBe('image/png');
    expect(context.drawImage.mock.calls).toEqual([
      [f.base, 0, 0],
      [f.deck, 0, 0],
    ]);
    expect([...f.handlers.values()].every((set) => set.size === 0)).toBe(true);
    expect(vi.getTimerCount()).toBe(0);
  });

  it('does not admit incomplete tiles at idle or at the observation frame', async () => {
    const f = fixture();
    f.map.areTilesLoaded.mockReturnValue(false);
    const result = f.capture();
    f.fire('idle');
    expect(f.overlay.setProps).not.toHaveBeenCalled();
    f.map.areTilesLoaded.mockReturnValue(true);
    f.fire('idle');
    f.map.areTilesLoaded.mockReturnValue(false);
    f.frame();
    expect(context.drawImage).not.toHaveBeenCalled();
    f.controller.abort();
    await expect(result).rejects.toMatchObject({ name: 'AbortError' });
  });

  it.each(['error', 'webglcontextlost'])('rejects %s and removes its listeners', async (event) => {
    const f = fixture();
    const result = f.capture();
    if (event === 'error') f.fire(event);
    else f.deck.dispatchEvent(new Event(event));
    await expect(result).rejects.toThrow('failed');
    expect(vi.getTimerCount()).toBe(0);
  });

  it('rejects mutation during asynchronous PNG encoding', async () => {
    const f = fixture();
    let encoded: BlobCallback = () => undefined;
    vi.spyOn(HTMLCanvasElement.prototype, 'toBlob').mockImplementation((done) => {
      encoded = done;
    });
    const result = f.capture();
    f.fire('idle');
    f.frame();
    f.unchanged.mockReturnValue(false);
    encoded(new Blob(['png'], { type: 'image/png' }));
    await expect(result).rejects.toThrow('changed');
  });

  it('aborts before readiness and ignores late frames', async () => {
    const f = fixture();
    const result = f.capture();
    f.fire('idle');
    f.controller.abort();
    f.frame();
    await expect(result).rejects.toMatchObject({ name: 'AbortError' });
    expect(context.drawImage).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('has a finite wait for missing imagery', async () => {
    const f = fixture();
    const result = f.capture();
    const assertion = expect(result).rejects.toThrow('timed out');
    await vi.advanceTimersByTimeAsync(CAPTURE_TIMEOUT_MS);
    await assertion;
  });

  it.each([
    null,
    new Blob(['x'], { type: 'text/plain' }),
    new Blob([new Uint8Array(8 * 1024 * 1024 + 1)], { type: 'image/png' }),
  ])('rejects invalid or oversized encoding', async (blob) => {
    vi.spyOn(HTMLCanvasElement.prototype, 'toBlob').mockImplementation((done) => done(blob));
    const f = fixture();
    const result = f.capture();
    f.fire('idle');
    f.frame();
    await expect(result).rejects.toThrow('encoding');
  });

  it('rejects a cleared basemap, dimensions mismatch and oversized buffers', () => {
    const f = fixture();
    context.getImageData.mockReturnValue({ data: new Uint8ClampedArray(8) });
    expect(() => compositeMapCanvases(f.base, f.deck)).toThrow('empty or uniform');
    f.deck.width = 90;
    expect(() => compositeMapCanvases(f.base, f.deck)).toThrow('resizing');
    f.base.width = 1601;
    expect(() => compositeMapCanvases(f.base, f.deck)).toThrow('dimensions');
  });

  it('reports origin-tainted readback explicitly', () => {
    const f = fixture();
    context.getImageData.mockImplementation(() => {
      throw new DOMException('tainted', 'SecurityError');
    });
    expect(() => compositeMapCanvases(f.base, f.deck)).toThrow('cross-origin');
  });
});
