import { MapLibreOverlay } from '@deck.gl/maplibre';
import type { Layer } from '@deck.gl/core';
import type { Map as MapLibreMap } from 'maplibre-gl';
import type { EngineOptions, MapRenderStatus } from './MapEngine';

const RECOVERY_DELAY_MS = 250;
const RESTORE_TIMEOUT_MS = 10_000;
const MAX_OVERLAY_RECOVERIES = 2;

/** Own the separate overlay context and bound recovery, retaining only the newest layer set. */
export class MapOverlayController {
  overlay: MapLibreOverlay | null = null;
  private layers: readonly Layer[] = [];
  private canvas: HTMLCanvasElement | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private mapLost = false;
  private destroyed = false;
  private recoveries = 0;
  private generation = 0;

  constructor(
    private readonly map: MapLibreMap,
    private readonly options: EngineOptions,
    private readonly invalidate: () => void,
  ) {
    map.on('webglcontextlost', this.onMapLost);
    map.on('webglcontextrestored', this.onMapRestored);
    this.create();
  }

  private status(status: MapRenderStatus, message = '') {
    this.options.onRenderStatus?.(status, message);
  }

  private clearTimer() {
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = null;
  }

  private listenToCanvas = () => {
    if (this.destroyed) return;
    const canvas = this.overlay?.getCanvas() ?? null;
    if (canvas === this.canvas) return;
    this.canvas?.removeEventListener('webglcontextlost', this.onOverlayLost);
    this.canvas = canvas;
    canvas?.addEventListener('webglcontextlost', this.onOverlayLost);
  };

  private create() {
    if (this.destroyed || this.mapLost) return;
    const generation = ++this.generation;
    const current = () => !this.destroyed && this.generation === generation;
    try {
      this.overlay = new MapLibreOverlay({
        interleaved: false,
        layers: [...this.layers],
        useDevicePixels: this.options.captureEnabled
          ? 1
          : Math.min(window.devicePixelRatio || 1, 1.5),
        onLoad: () => {
          if (current()) this.listenToCanvas();
        },
        onError: () => {
          if (current()) this.onError();
        },
      });
      this.map.addControl(this.overlay);
      this.listenToCanvas();
      this.status('ready');
    } catch {
      this.onError();
    }
  }

  private disposeOverlay() {
    // Async renderer callbacks may outlive finalize and must not touch the next instance.
    this.generation += 1;
    this.canvas?.removeEventListener('webglcontextlost', this.onOverlayLost);
    this.canvas = null;
    const overlay = this.overlay;
    this.overlay = null;
    // Finalize removes the control, listeners, canvas and GPU allocations.
    try {
      overlay?.finalize();
    } catch {
      this.status('failed', 'Map graphics cleanup failed. Reload the map to retry.');
    }
  }

  private onError = () => {
    if (this.destroyed) return;
    this.generation += 1;
    this.invalidate();
    this.clearTimer();
    this.status('failed', 'Map overlays could not be drawn. Reload the map to retry.');
    // Defer disposal out of the renderer's own callback stack.
    this.timer = setTimeout(() => {
      this.timer = null;
      this.disposeOverlay();
    }, 0);
  };

  private onOverlayLost = (event: Event) => {
    event.preventDefault();
    this.generation += 1;
    this.invalidate();
    this.clearTimer();
    if (this.options.captureEnabled || this.recoveries >= MAX_OVERLAY_RECOVERIES) {
      this.onError();
      return;
    }
    this.status('recovering', 'Restoring map overlays after a graphics interruption.');
    this.timer = setTimeout(() => {
      this.timer = null;
      this.disposeOverlay();
      this.recoveries += 1;
      this.create();
    }, RECOVERY_DELAY_MS);
  };

  private onMapLost = () => {
    this.mapLost = true;
    this.invalidate();
    this.clearTimer();
    this.disposeOverlay();
    this.status('recovering', 'Waiting for the map graphics context to recover.');
    this.timer = setTimeout(() => {
      this.timer = null;
      this.status('failed', 'The map graphics context did not recover. Reload the map to retry.');
    }, RESTORE_TIMEOUT_MS);
  };

  private onMapRestored = () => {
    if (!this.mapLost || this.destroyed) return;
    this.mapLost = false;
    this.clearTimer();
    if (!this.options.captureEnabled) this.create();
  };

  setLayers(layers: readonly Layer[]) {
    this.layers = layers;
    if (!this.overlay || this.mapLost || this.timer !== null) return;
    try {
      this.overlay.setProps({ layers: [...layers] });
    } catch {
      this.onError();
    }
  }

  pickObjectsAt(x: number, y: number): readonly unknown[] {
    if (!this.overlay || this.mapLost || this.timer !== null) return [];
    try {
      return this.overlay
        .pickMultipleObjects({ x, y, radius: 4, depth: 8 })
        .map((hit) => hit.object as unknown);
    } catch {
      this.onError();
      return [];
    }
  }

  destroy() {
    this.destroyed = true;
    this.clearTimer();
    this.map.off('webglcontextlost', this.onMapLost);
    this.map.off('webglcontextrestored', this.onMapRestored);
    this.disposeOverlay();
    this.layers = [];
  }
}
