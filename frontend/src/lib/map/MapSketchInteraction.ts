import type { CursorPosition, SketchDrag, SketchDragHandler, SketchMode } from './MapEngine';

interface SketchMap {
  getCanvas(): HTMLCanvasElement;
  unproject(point: [number, number]): { lng: number; lat: number };
  dragPan: { isEnabled(): boolean; enable(): void; disable(): void };
}
interface ActiveDrag {
  pointerId: number;
  start: CursorPosition;
  current: CursorPosition;
  panEnabled: boolean;
}

/** Canvas-only gestures keep UI clicks and normal map navigation independent of sketches. */
export class MapSketchInteraction {
  private readonly canvas: HTMLCanvasElement;
  private readonly handlers = new Set<SketchDragHandler>();
  private readonly originalCursor: string;
  private readonly originalTouchAction: string;
  private mode: SketchMode = 'navigate';
  private active: ActiveDrag | null = null;
  private frame: number | null = null;
  private suppressUntil = 0;

  constructor(
    private readonly map: SketchMap,
    private readonly stopMotion: () => void,
  ) {
    this.canvas = map.getCanvas();
    this.originalCursor = this.canvas.style.cursor;
    this.originalTouchAction = this.canvas.style.touchAction;
    this.canvas.addEventListener('pointerdown', this.down, true);
    this.canvas.addEventListener('pointermove', this.move, true);
    this.canvas.addEventListener('pointerup', this.up, true);
    this.canvas.addEventListener('pointercancel', this.cancelPointer, true);
    this.canvas.addEventListener('lostpointercapture', this.cancelPointer, true);
    this.canvas.addEventListener('click', this.click, true);
    window.addEventListener('keydown', this.key);
    window.addEventListener('blur', this.cancel);
  }

  onDrag(handler: SketchDragHandler): () => void {
    this.handlers.add(handler);
    return () => {
      this.handlers.delete(handler);
    };
  }

  setMode(mode: SketchMode): void {
    if (this.mode !== mode) {
      this.cancel();
      if (mode !== 'navigate') this.stopMotion();
    }
    this.mode = mode;
    this.canvas.style.cursor = mode === 'navigate' ? this.originalCursor : 'crosshair';
    this.canvas.style.touchAction = mode === 'drag' ? 'none' : this.originalTouchAction;
  }

  suppressesClick(): boolean {
    return this.active !== null || performance.now() < this.suppressUntil;
  }

  private position(event: PointerEvent): CursorPosition | null {
    const box = this.canvas.getBoundingClientRect();
    try {
      const point = this.map.unproject([event.clientX - box.left, event.clientY - box.top]);
      if (!Number.isFinite(point.lng) || !Number.isFinite(point.lat) || Math.abs(point.lat) > 90)
        return null;
      return { lon: (((point.lng % 360) + 540) % 360) - 180, lat: point.lat };
    } catch {
      return null;
    }
  }

  private emit(phase: SketchDrag['phase'], drag: ActiveDrag): void {
    for (const handler of this.handlers)
      handler({ phase, start: { ...drag.start }, current: { ...drag.current } });
  }

  private down = (event: PointerEvent) => {
    if (event.target !== this.canvas || event.button !== 0 || !event.isPrimary) return;
    this.suppressUntil = 0;
    if (this.mode !== 'drag' || this.active) return;
    const position = this.position(event);
    if (!position) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    this.stopMotion();
    const drag: ActiveDrag = {
      pointerId: event.pointerId,
      start: position,
      current: position,
      panEnabled: this.map.dragPan.isEnabled(),
    };
    this.active = drag;
    this.map.dragPan.disable();
    try {
      this.canvas.setPointerCapture(event.pointerId);
    } catch {
      this.finish('cancel');
      return;
    }
    this.emit('start', drag);
  };

  private move = (event: PointerEvent) => {
    const drag = this.active;
    if (event.pointerId !== drag?.pointerId) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const position = this.position(event);
    if (!position) return;
    drag.current = position;
    this.frame ??= requestAnimationFrame(() => {
      this.frame = null;
      if (this.active === drag) this.emit('move', drag);
    });
  };

  private up = (event: PointerEvent) => {
    if (event.pointerId !== this.active?.pointerId) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const position = this.position(event);
    if (position) this.active.current = position;
    this.finish(position ? 'end' : 'cancel');
  };

  private finish(phase: 'end' | 'cancel'): void {
    const drag = this.active;
    if (!drag) return;
    this.active = null;
    if (this.frame !== null) cancelAnimationFrame(this.frame);
    this.frame = null;
    this.suppressUntil = performance.now() + 500;
    if (drag.panEnabled) this.map.dragPan.enable();
    else this.map.dragPan.disable();
    try {
      if (this.canvas.hasPointerCapture(drag.pointerId))
        this.canvas.releasePointerCapture(drag.pointerId);
    } catch {
      /* Pointer capture can already be gone after window or graphics loss. */
    }
    this.emit(phase, drag);
  }

  cancel = () => {
    this.finish('cancel');
  };
  private cancelPointer = (event: PointerEvent) => {
    if (event.pointerId === this.active?.pointerId) this.cancel();
  };
  private key = (event: KeyboardEvent) => {
    if (event.key === 'Escape' && this.active) {
      event.preventDefault();
      this.cancel();
    }
  };
  private click = (event: MouseEvent) => {
    if (this.suppressesClick()) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  };

  destroy(): void {
    this.cancel();
    this.handlers.clear();
    this.canvas.style.cursor = this.originalCursor;
    this.canvas.style.touchAction = this.originalTouchAction;
    this.canvas.removeEventListener('pointerdown', this.down, true);
    this.canvas.removeEventListener('pointermove', this.move, true);
    this.canvas.removeEventListener('pointerup', this.up, true);
    this.canvas.removeEventListener('pointercancel', this.cancelPointer, true);
    this.canvas.removeEventListener('lostpointercapture', this.cancelPointer, true);
    this.canvas.removeEventListener('click', this.click, true);
    window.removeEventListener('keydown', this.key);
    window.removeEventListener('blur', this.cancel);
  }
}
