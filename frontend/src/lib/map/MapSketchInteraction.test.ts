import { afterEach, expect, it, vi } from 'vitest';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import { MapSketchInteraction } from './MapSketchInteraction';
import { createMapLibreEngine } from './MapLibreEngine';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));

const cleanups: (() => void)[] = [];
afterEach(() => {
  cleanups.splice(0).forEach((cleanup) => cleanup());
  vi.restoreAllMocks();
});
function setup(pan = true) {
  const map = new FakeMap({});
  if (!pan) map.dragPan.disable();
  const canvas = map.getCanvas();
  const capture = vi.spyOn(canvas, 'setPointerCapture');
  const release = vi.spyOn(canvas, 'releasePointerCapture');
  canvas.style.cursor = 'grab';
  canvas.style.touchAction = 'pan-y';
  const stop = vi.fn();
  const gestures = new MapSketchInteraction(map, stop);
  const handler = vi.fn();
  gestures.onDrag(handler);
  cleanups.push(() => gestures.destroy());
  const pointer = (type: string, x = 0, y = 0, options: Record<string, unknown> = {}) => {
    const event = new MouseEvent(type, {
      clientX: x,
      clientY: y,
      bubbles: true,
      cancelable: true,
      button: 0,
    });
    Object.defineProperties(
      event,
      Object.fromEntries(
        Object.entries({ pointerId: 1, isPrimary: true, ...options }).map(([key, value]) => [
          key,
          { value },
        ]),
      ),
    );
    canvas.dispatchEvent(event);
    return event;
  };
  return { map, canvas, gestures, handler, stop, pointer, capture, release };
}

it('keeps navigation and point picking draggable, applies and restores the cursor', () => {
  const { gestures, canvas, pointer, handler, map } = setup();
  gestures.setMode('points');
  expect(canvas.style.cursor).toBe('crosshair');
  pointer('pointerdown', 1, 2);
  expect(handler).not.toHaveBeenCalled();
  expect(map.dragPan.isEnabled()).toBe(true);
  gestures.setMode('navigate');
  expect(canvas.style.cursor).toBe('grab');
});

it('captures primary drags, coalesces moves and commits the final release coordinate', () => {
  const { gestures, canvas, pointer, handler, map, stop, capture, release } = setup();
  const raf = vi.spyOn(window, 'requestAnimationFrame').mockReturnValue(12);
  const cancel = vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => undefined);
  gestures.setMode('drag');
  pointer('pointerdown', 1, 2);
  expect(stop).toHaveBeenCalledTimes(2);
  expect(map.dragPan.isEnabled()).toBe(false);
  expect(capture).toHaveBeenCalledWith(1);
  pointer('pointermove', 3, 4);
  pointer('pointermove', 5, 6);
  expect(raf).toHaveBeenCalledOnce();
  raf.mock.calls[0]![0](0);
  expect(handler).toHaveBeenLastCalledWith({
    phase: 'move',
    start: { lon: 1, lat: 2 },
    current: { lon: 5, lat: 6 },
  });
  pointer('pointermove', 7, 8);
  pointer('pointerup', 9, 10);
  expect(handler).toHaveBeenLastCalledWith({
    phase: 'end',
    start: { lon: 1, lat: 2 },
    current: { lon: 9, lat: 10 },
  });
  expect(cancel).toHaveBeenCalledWith(12);
  expect(map.dragPan.isEnabled()).toBe(true);
  expect(release).toHaveBeenCalledWith(1);
  const click = new MouseEvent('click', { bubbles: true, cancelable: true });
  canvas.dispatchEvent(click);
  expect(click.defaultPrevented).toBe(true);
  gestures.setMode('points');
  pointer('pointerdown', 1, 2);
  expect(gestures.suppressesClick()).toBe(false);
});

it.each(['escape', 'cancel', 'lost', 'blur', 'mode', 'destroy'] as const)(
  'cancels on %s and preserves an originally disabled pan control',
  (cause) => {
    const { gestures, pointer, handler, map, canvas } = setup(false);
    gestures.setMode('drag');
    pointer('pointerdown', 1, 2);
    if (cause === 'escape') window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    if (cause === 'cancel') pointer('pointercancel');
    if (cause === 'lost') pointer('lostpointercapture');
    if (cause === 'blur') window.dispatchEvent(new Event('blur'));
    if (cause === 'mode') gestures.setMode('points');
    if (cause === 'destroy') gestures.destroy();
    expect(handler).toHaveBeenLastCalledWith({
      phase: 'cancel',
      start: { lon: 1, lat: 2 },
      current: { lon: 1, lat: 2 },
    });
    expect(map.dragPan.isEnabled()).toBe(false);
    const count = handler.mock.calls.length;
    pointer('pointerup', 3, 4);
    expect(handler).toHaveBeenCalledTimes(count);
    if (cause === 'destroy') {
      expect(canvas.style.cursor).toBe('grab');
      expect(canvas.style.touchAction).toBe('pan-y');
    }
  },
);

it('rejects secondary pointers, invalid coordinates and unavailable pointer capture', () => {
  const { gestures, pointer, handler, map, capture } = setup();
  gestures.setMode('drag');
  pointer('pointerdown', 1, 2, { isPrimary: false });
  pointer('pointerdown', 1, 2, { button: 2 });
  pointer('pointerdown', 1, 91);
  expect(handler).not.toHaveBeenCalled();
  capture.mockImplementation(() => {
    throw new Error('gone');
  });
  pointer('pointerdown', 1, 2);
  expect(handler).toHaveBeenLastCalledWith(expect.objectContaining({ phase: 'cancel' }));
  expect(map.dragPan.isEnabled()).toBe(true);
});

it('ignores foreign pointers, wraps longitudes and cancels invalid release positions', () => {
  const { gestures, pointer, handler, map } = setup();
  gestures.setMode('drag');
  pointer('pointerdown', 361, 2);
  pointer('pointermove', 3, 4, { pointerId: 2 });
  pointer('pointerup', 3, 4, { pointerId: 2 });
  expect(handler).toHaveBeenCalledOnce();
  map.unproject.mockImplementation(() => {
    throw new Error('unproject failed');
  });
  pointer('pointerup');
  expect(handler).toHaveBeenLastCalledWith({
    phase: 'cancel',
    start: { lon: 1, lat: 2 },
    current: { lon: 1, lat: 2 },
  });
});

it.each(['projection', 'style', 'graphics', 'overlay', 'destroy'] as const)(
  'cancels an engine gesture on %s changes and suppresses a stale map click',
  (change) => {
    const engine = createMapLibreEngine();
    engine.mount(document.createElement('div'));
    cleanups.push(() => engine.destroy());
    const map = FakeMap.instances.at(-1)!;
    const handler = vi.fn();
    const clicked = vi.fn();
    engine.onDrag?.(handler);
    engine.on('click', clicked);
    engine.setSketchMode?.('drag');
    const down = new MouseEvent('pointerdown', {
      clientX: 1,
      clientY: 2,
      button: 0,
      bubbles: true,
    });
    Object.defineProperties(down, { pointerId: { value: 1 }, isPrimary: { value: true } });
    map.getCanvas().dispatchEvent(down);
    expect(map.dragPan.isEnabled()).toBe(false);
    if (change === 'projection') engine.setProjection('mercator');
    if (change === 'style') engine.setBaseLayer('light');
    if (change === 'graphics') map.fire('webglcontextlost');
    if (change === 'overlay')
      MapboxOverlay.instances
        .at(-1)!
        .canvas.dispatchEvent(new Event('webglcontextlost', { cancelable: true }));
    if (change === 'destroy') engine.destroy();
    expect(map.dragPan.isEnabled()).toBe(true);
    expect(handler).toHaveBeenLastCalledWith(expect.objectContaining({ phase: 'cancel' }));
    if (change !== 'destroy') {
      map.fire('click', { lngLat: { lng: 1, lat: 2 } });
      expect(clicked).not.toHaveBeenCalled();
    }
  },
);
