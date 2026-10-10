import { act, fireEvent, render } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { EyeReply, EyeRequest } from './evilEyeProtocol';

vi.unmock('./EvilEye');
vi.unmock('./EvilEyeSurface');
const graphics = vi.hoisted(() => ({
  create: vi.fn(),
  render: vi.fn(),
  dispose: vi.fn(),
  resize: vi.fn(),
  noise: new Uint8Array([1, 2, 3, 4]),
}));
vi.mock('./evilEyeRenderer', () => ({
  eyeNoise: () => graphics.noise,
  createEyeRenderer: graphics.create,
}));
vi.mock('./evilEyeNoise', () => ({ eyeNoise: () => graphics.noise }));
import EvilEye from './EvilEye';

class FakeWorker {
  static instances: FakeWorker[] = [];
  onmessage: ((event: MessageEvent<EyeReply>) => void) | null = null;
  onerror: (() => void) | null = null;
  onmessageerror: (() => void) | null = null;
  postMessage = vi.fn<(message: EyeRequest, transfer: Transferable[]) => void>();
  terminate = vi.fn();
  constructor() {
    FakeWorker.instances.push(this);
  }
  reply(data: EyeReply) {
    act(() => this.onmessage?.({ data } as MessageEvent<EyeReply>));
  }
  frames() {
    return this.postMessage.mock.calls.map(([data]) => data).filter((x) => x.type === 'frame');
  }
}
const frames = new Map<number, FrameRequestCallback>();
let next = 0;
function frame(time: number) {
  const entry = [...frames.entries()][0];
  if (!entry) throw new Error('No document frame scheduled');
  frames.delete(entry[0]);
  act(() => entry[1](time));
}
function currentWorker() {
  return FakeWorker.instances.at(-1)!;
}

beforeEach(() => {
  vi.useFakeTimers();
  FakeWorker.instances.length = 0;
  frames.clear();
  graphics.create.mockReset().mockImplementation(() => ({
    render: graphics.render,
    resize: graphics.resize,
    dispose: graphics.dispose,
  }));
  vi.stubGlobal('Worker', FakeWorker);
  vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
    frames.set(++next, cb);
    return next;
  });
  vi.stubGlobal('cancelAnimationFrame', (id: number) => frames.delete(id));
  Object.defineProperty(HTMLCanvasElement.prototype, 'transferControlToOffscreen', {
    configurable: true,
    value: vi.fn(() => ({ width: 300, height: 150 })),
  });
});
afterEach(() => {
  vi.runOnlyPendingTimers();
  vi.useRealTimers();
  Reflect.deleteProperty(HTMLCanvasElement.prototype, 'transferControlToOffscreen');
});

describe('public offscreen eye ownership', () => {
  it('leaves existing callers synchronous and falls back when workers are unsupported', () => {
    const ordinary = render(<EvilEye />);
    expect(FakeWorker.instances).toHaveLength(0);
    expect(graphics.create).toHaveBeenCalledTimes(1);
    ordinary.unmount();
    vi.stubGlobal('Worker', undefined);
    render(<EvilEye workerRendering />);
    expect(graphics.create).toHaveBeenCalledTimes(2);
  });

  it('waits for viewport entry, readiness and a real first frame without detaching noise', () => {
    let enter: IntersectionObserverCallback | undefined;
    const disconnect = vi.fn();
    vi.stubGlobal(
      'IntersectionObserver',
      class {
        constructor(callback: IntersectionObserverCallback) {
          enter = callback;
        }
        observe = vi.fn();
        disconnect = disconnect;
      },
    );
    const { container, unmount } = render(<EvilEye workerRendering deferUntilVisible />);
    expect(FakeWorker.instances).toHaveLength(0);
    act(() =>
      enter?.([{ isIntersecting: true } as IntersectionObserverEntry], {} as IntersectionObserver),
    );
    const worker = currentWorker();
    expect(disconnect).toHaveBeenCalled();
    const [init, transfer] = worker.postMessage.mock.calls[0]!;
    expect(init.type).toBe('init');
    if (init.type !== 'init') throw new Error('Expected worker initialisation');
    expect(transfer).toEqual([init.canvas]);
    expect(transfer).not.toContain(graphics.noise.buffer);
    expect(init.noise).toBe(graphics.noise);
    expect(graphics.noise.byteLength).toBe(4);
    expect(graphics.create).not.toHaveBeenCalled();
    frame(1000);
    expect(worker.frames()).toHaveLength(0);
    worker.reply({ type: 'ready' });
    expect(container.querySelector('img')).toBeVisible();
    frame(1016);
    expect(container.querySelector('img')).toBeVisible();
    worker.reply({ type: 'frame' });
    expect(container.querySelector('img')).not.toBeVisible();
    const queued = worker.onmessage!;
    unmount();
    act(() => queued({ data: { type: 'failed', phase: 'startup' } } as MessageEvent<EyeReply>));
    expect(graphics.create).not.toHaveBeenCalled();
    worker.reply({ type: 'disposed' });
    expect(worker.terminate).toHaveBeenCalledOnce();
    expect(frames.size).toBe(0);
  });

  it('preserves document timestamps, per-render interpolation, cap and pause with one frame in flight', () => {
    const { container, rerender } = render(<EvilEye workerRendering maxFps={24} />);
    const surface = container.querySelector('canvas')!.parentElement!;
    vi.spyOn(surface, 'getBoundingClientRect').mockReturnValue({
      left: 0,
      top: 0,
      width: 100,
      height: 100,
      right: 100,
      bottom: 100,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    });
    const worker = currentWorker();
    worker.reply({ type: 'ready' });
    fireEvent.mouseMove(surface, { clientX: 100, clientY: 0 });
    frame(1000);
    frame(1016);
    frame(1048); // Busy: neither queue another frame nor advance interpolation.
    expect(worker.frames()).toEqual([
      { type: 'frame', frame: { time: 1000, mouse: [0.05, 0.05] } },
    ]);
    worker.reply({ type: 'frame' });
    frame(1064);
    expect(worker.frames().at(-1)).toEqual({
      type: 'frame',
      frame: { time: 1064, mouse: [0.0975, 0.0975] },
    });
    worker.reply({ type: 'frame' });
    frame(1080);
    expect(worker.frames()).toHaveLength(2);
    rerender(<EvilEye workerRendering maxFps={24} paused />);
    frame(1100);
    expect(frames.size).toBe(0);
    rerender(<EvilEye workerRendering maxFps={24} />);
    fireEvent.mouseLeave(surface);
    frame(1200);
    expect(worker.frames().at(-1)?.frame.mouse).toEqual([0.092625, 0.092625]);
    expect(FakeWorker.instances).toHaveLength(1);
  });

  it('sends responsive sizes and preserves initially paused and reduced-motion values', () => {
    const { container, rerender } = render(
      <EvilEye workerRendering paused maxFps={1} flameSpeed={0} pupilFollow={0} />,
    );
    const worker = currentWorker();
    const init = worker.postMessage.mock.calls[0]![0];
    expect(init).toMatchObject({ type: 'init', options: { flameSpeed: 0, pupilFollow: 0 } });
    worker.reply({ type: 'ready' });
    expect(frames.size).toBe(0);
    expect(container.querySelector('img')).toBeVisible();
    const surface = container.querySelector('canvas')!.parentElement!;
    Object.defineProperties(surface, { offsetWidth: { value: 180 }, offsetHeight: { value: 90 } });
    fireEvent(window, new Event('resize'));
    expect(worker.postMessage).toHaveBeenLastCalledWith(
      { type: 'resize', size: { width: 180, height: 90 } },
      [],
    );
    expect(container.querySelector('canvas')).toHaveStyle({ width: '180px', height: '90px' });
    worker.reply({ type: 'resized' });
    rerender(<EvilEye workerRendering maxFps={1} flameSpeed={0} pupilFollow={0} />);
    frame(1000);
    worker.reply({ type: 'frame' });
    frame(1500);
    expect(worker.frames()).toHaveLength(1);
    frame(2000);
    expect(worker.frames()).toHaveLength(2);
    expect(FakeWorker.instances).toHaveLength(1);
  });

  it.each(['error', 'timeout', 'failed'] as const)(
    'replaces a transferred canvas after startup %s',
    (kind) => {
      const { container } = render(<EvilEye workerRendering />);
      const original = container.querySelector('canvas');
      const worker = currentWorker();
      const queued = worker.onmessage!;
      if (kind === 'error') act(() => worker.onerror?.());
      else if (kind === 'timeout')
        act(() => {
          vi.advanceTimersByTime(5000);
        });
      else worker.reply({ type: 'failed', phase: 'startup' });
      expect(worker.terminate).toHaveBeenCalledOnce();
      expect(container.querySelector('canvas')).not.toBe(original);
      expect(graphics.create.mock.calls[0]?.[0]).toBe(container.querySelector('canvas'));
      expect(container.querySelector('img')).toBeVisible();
      act(() => queued({ data: { type: 'ready' } } as MessageEvent<EyeReply>));
      frame(1000);
      expect(graphics.render).toHaveBeenCalled();
      expect(container.querySelector('img')).not.toBeVisible();
      expect(FakeWorker.instances).toHaveLength(1);
    },
  );

  it('keeps context loss terminal and ignores stale messages after prop replacement', () => {
    const { container, rerender } = render(<EvilEye workerRendering />);
    const old = currentWorker();
    const queued = old.onmessage!;
    rerender(<EvilEye workerRendering eyeColor="#123456" />);
    const worker = currentWorker();
    act(() => queued({ data: { type: 'failed', phase: 'startup' } } as MessageEvent<EyeReply>));
    expect(graphics.create).not.toHaveBeenCalled();
    worker.reply({ type: 'failed', phase: 'lost' });
    expect(container.querySelector('canvas')).toBeNull();
    expect(container.querySelector('img')).toBeVisible();
    rerender(<EvilEye workerRendering paused />);
    rerender(<EvilEye workerRendering />);
    expect(FakeWorker.instances).toHaveLength(2);
    expect(graphics.create).not.toHaveBeenCalled();
    expect(frames.size).toBe(0);
  });
});
