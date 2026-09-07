import type { Map as MapLibreMap } from 'maplibre-gl';
import type { MapboxOverlay } from '@deck.gl/mapbox';

export const CAPTURE_TIMEOUT_MS = 30_000;
const MAX_PIXELS = 4_000_000;
const MAX_BYTES = 8 * 1024 * 1024;

/** Read both real render surfaces synchronously while Deck's drawing buffer is valid. */
export function compositeMapCanvases(
  base: HTMLCanvasElement,
  overlay: HTMLCanvasElement,
): HTMLCanvasElement {
  const { width, height } = base;
  if (width < 1 || height < 1 || width > 1600 || height > 1000 || width * height > MAX_PIXELS) {
    throw new Error('Map export dimensions must be between 1×1 and 1600×1000 pixels.');
  }
  if (overlay.width !== width || overlay.height !== height) {
    throw new Error('Map and observation canvases have not finished resizing.');
  }
  const output = document.createElement('canvas');
  output.width = width;
  output.height = height;
  const context = output.getContext('2d');
  if (!context) throw new Error('Map image capture requires a canvas renderer.');
  try {
    context.drawImage(base, 0, 0);
    // Reject cleared or uniform base buffers rather than returning an empty "map".
    const pixels = context.getImageData(0, 0, width, height).data;
    let varied = false;
    for (let index = 4; index < pixels.length; index += 4) {
      if (
        pixels[index] !== pixels[0] ||
        pixels[index + 1] !== pixels[1] ||
        pixels[index + 2] !== pixels[2] ||
        pixels[index + 3] !== pixels[3]
      ) {
        varied = true;
        break;
      }
    }
    if (!varied) throw new Error('The base map drawing buffer is empty or uniform.');
    context.drawImage(overlay, 0, 0);
    // Forces an origin-clean readback after including the observation canvas too.
    context.getImageData(0, 0, 1, 1);
  } catch (error) {
    if (error instanceof DOMException && error.name === 'SecurityError') {
      throw new Error('Map imagery does not permit image export (cross-origin readback).');
    }
    throw error;
  }
  return output;
}

/**
 * Wait for an idle basemap, then a real Deck frame with loaded layers. Only the
 * dedicated export map animates during this bounded wait; copying happens inside
 * onAfterRender, before WebGL is allowed to clear the observation buffer.
 */
export function captureMapImage(
  map: MapLibreMap,
  overlay: MapboxOverlay,
  signal: AbortSignal,
  unchanged: () => boolean,
  layersLoaded: () => boolean,
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    let settled = false;
    let rendering = false;
    let encoding = false;
    const base = map.getCanvas();
    const deckCanvas = overlay.getCanvas();
    const cleanup = () => {
      clearTimeout(timeout);
      signal.removeEventListener('abort', abort);
      map.off('idle', idle);
      map.off('render', check);
      map.off('error', failRender);
      base.removeEventListener('webglcontextlost', failRender);
      deckCanvas?.removeEventListener('webglcontextlost', failRender);
      overlay.setProps({ _animate: false, onAfterRender: () => undefined });
    };
    const fail = (error: Error) => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(error);
    };
    const abort = () => fail(new DOMException('Map image capture cancelled.', 'AbortError'));
    const failRender = () => fail(new Error('A map renderer or imagery request failed.'));
    const check = () => {
      if (!unchanged()) fail(new Error('The map changed during image capture. Try again.'));
      return !settled;
    };
    const afterRender = () => {
      if (!check() || encoding || !map.loaded() || !map.areTilesLoaded() || !layersLoaded()) return;
      try {
        const canvas = overlay.getCanvas();
        if (!canvas) throw new Error('The observation renderer is unavailable.');
        const output = compositeMapCanvases(base, canvas);
        encoding = true;
        overlay.setProps({ _animate: false });
        output.toBlob((blob) => {
          if (!check()) return;
          if (blob?.type !== 'image/png' || blob.size < 1 || blob.size > MAX_BYTES) {
            fail(new Error('Map image encoding failed or exceeded the 8 MiB limit.'));
            return;
          }
          settled = true;
          cleanup();
          resolve(blob);
        }, 'image/png');
      } catch (error) {
        fail(error instanceof Error ? error : new Error('Map image capture failed.'));
      }
    };
    const idle = () => {
      if (!check() || rendering || !map.loaded() || !map.areTilesLoaded()) return;
      rendering = true;
      overlay.setProps({ _animate: true, onAfterRender: afterRender });
      map.triggerRepaint();
    };
    const timeout = setTimeout(
      () => fail(new Error('Map image capture timed out waiting for imagery.')),
      CAPTURE_TIMEOUT_MS,
    );
    if (signal.aborted) {
      abort();
      return;
    }
    signal.addEventListener('abort', abort, { once: true });
    map.on('idle', idle);
    map.on('render', check);
    map.on('error', failRender);
    base.addEventListener('webglcontextlost', failRender);
    deckCanvas?.addEventListener('webglcontextlost', failRender);

    // Request a real idle cycle even if tiles were already cached.
    map.triggerRepaint();
  });
}
