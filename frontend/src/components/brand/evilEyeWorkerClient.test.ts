import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { EyeOptions, EyeReply, EyeRequest } from './evilEyeProtocol';

vi.mock('./evilEyeNoise', () => ({ eyeNoise: () => new Uint8Array(4) }));
import { createEyeWorker } from './evilEyeWorkerClient';

class FakeWorker {
  static instance: FakeWorker;
  onmessage: ((event: MessageEvent<EyeReply>) => void) | null = null;
  onerror: (() => void) | null = null;
  onmessageerror: (() => void) | null = null;
  postMessage = vi.fn<(message: EyeRequest, transfer: Transferable[]) => void>();
  terminate = vi.fn();
  constructor() {
    FakeWorker.instance = this;
  }
  reply(data: EyeReply) {
    this.onmessage?.({ data } as MessageEvent<EyeReply>);
  }
}
beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal('Worker', FakeWorker);
});
afterEach(() => {
  vi.runOnlyPendingTimers();
  vi.useRealTimers();
});

function setup(transfer = () => ({}) as OffscreenCanvas) {
  const canvas = document.createElement('canvas');
  canvas.transferControlToOffscreen = transfer;
  const onFrame = vi.fn(),
    onStartup = vi.fn(),
    onFailure = vi.fn();
  const surface = createEyeWorker(
    canvas,
    {} as EyeOptions,
    { width: 80, height: 40 },
    onFrame,
    onStartup,
    onFailure,
  );
  return { surface, worker: FakeWorker.instance, onFrame, onStartup, onFailure };
}

describe('bounded offscreen transport failures', () => {
  it('returns synchronous fallback when canvas transfer or worker construction is unavailable', () => {
    const unsupported = createEyeWorker(
      document.createElement('canvas'),
      {} as EyeOptions,
      { width: 1, height: 1 },
      vi.fn(),
      vi.fn(),
      vi.fn(),
    );
    expect(unsupported).toBeNull();
    vi.stubGlobal(
      'Worker',
      class extends FakeWorker {
        constructor() {
          super();
          throw new Error('CSP or unsupported');
        }
      },
    );
    expect(setup().surface).toBeNull();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('terminates a created worker when canvas transfer throws', () => {
    const { surface, worker } = setup(() => {
      throw new Error('Already transferred');
    });
    expect(surface).toBeNull();
    expect(worker.terminate).toHaveBeenCalledOnce();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('terminates when posting a transferred canvas fails, leaving replacement to the caller', () => {
    vi.stubGlobal(
      'Worker',
      class extends FakeWorker {
        override postMessage = vi.fn(() => {
          throw new Error('Clone failed');
        });
      },
    );
    const { surface, worker, onStartup } = setup();
    expect(surface).toBeNull();
    expect(worker.terminate).toHaveBeenCalledOnce();
    expect(onStartup).not.toHaveBeenCalled();
  });

  it.each([false, true])('contains resize transport failure with a queued size (%s)', (ready) => {
    const { surface, worker, onStartup, onFailure } = setup();
    if (ready) worker.reply({ type: 'ready' });
    worker.postMessage.mockImplementation(() => {
      throw new Error('Worker stopped');
    });
    surface!.resize({ width: 160, height: 80 });
    if (!ready) worker.reply({ type: 'ready' });
    expect(onStartup).not.toHaveBeenCalled();
    expect(onFailure).toHaveBeenCalledOnce();
    surface!.resize({ width: 1, height: 1 });
    expect(worker.terminate).toHaveBeenCalledOnce();
  });

  it('coalesces startup and in-flight resize bursts, including an eye with no animation frames', () => {
    const { surface, worker } = setup();
    const sizes = () =>
      worker.postMessage.mock.calls.map(([data]) => data).filter((data) => data.type === 'resize');
    for (let width = 100; width <= 200; width++) surface!.resize({ width, height: 50 });
    expect(sizes()).toHaveLength(0);
    worker.reply({ type: 'ready' });
    expect(sizes()).toEqual([{ type: 'resize', size: { width: 200, height: 50 } }]);
    for (let width = 201; width <= 300; width++) surface!.resize({ width, height: 75 });
    expect(sizes()).toHaveLength(1);
    worker.reply({ type: 'resized' });
    expect(sizes().at(-1)).toEqual({ type: 'resize', size: { width: 300, height: 75 } });
    worker.reply({ type: 'resized' });
    // Matching the acknowledged dimensions does not reset the drawing buffer.
    surface!.resize({ width: 300, height: 75 });
    expect(sizes()).toHaveLength(2);
    expect(surface!.render({ time: 1000, mouse: [0, 0] })).toBe(true);
    for (let width = 301; width <= 400; width++) surface!.resize({ width, height: 100 });
    expect(sizes()).toHaveLength(2);
    expect(surface!.render({ time: 1016, mouse: [0, 0] })).toBe(false);
    worker.reply({ type: 'frame' });
    expect(sizes().at(-1)).toEqual({ type: 'resize', size: { width: 400, height: 100 } });
    worker.reply({ type: 'resized' });
    surface!.dispose();
    worker.reply({ type: 'disposed' });
  });

  it('makes an accepted worker render transport failure terminal', () => {
    const { surface, worker, onFailure, onFrame } = setup();
    worker.reply({ type: 'ready' });
    worker.reply({ type: 'frame' }); // Unsolicited acknowledgements cannot hide the capture.
    expect(onFrame).not.toHaveBeenCalled();
    worker.postMessage.mockImplementation(() => {
      throw new Error('Worker stopped');
    });
    expect(surface!.render({ time: 100, mouse: [0, 0] })).toBe(false);
    expect(onFailure).toHaveBeenCalledOnce();
    surface!.dispose();
    expect(worker.terminate).toHaveBeenCalledOnce();
  });

  it.each(['onerror', 'onmessageerror'] as const)(
    'contains %s after readiness without retrying',
    (event) => {
      const { worker, onFailure, onStartup } = setup();
      worker.reply({ type: 'ready' });
      worker[event]?.();
      expect(onFailure).toHaveBeenCalledOnce();
      expect(onStartup).not.toHaveBeenCalled();
      expect(worker.terminate).toHaveBeenCalledOnce();
    },
  );

  it('bounds unresponsive disposal and ignores already queued callbacks', () => {
    const { surface, worker, onFrame, onStartup } = setup();
    const queued = worker.onmessage!;
    surface!.dispose();
    surface!.dispose();
    expect(worker.postMessage).toHaveBeenLastCalledWith({ type: 'dispose' }, []);
    queued({ data: { type: 'failed', phase: 'startup' } } as MessageEvent<EyeReply>);
    expect(onStartup).not.toHaveBeenCalled();
    expect(onFrame).not.toHaveBeenCalled();
    vi.advanceTimersByTime(250);
    expect(worker.terminate).toHaveBeenCalledOnce();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('terminates immediately when the disposal message cannot be posted', () => {
    const { surface, worker } = setup();
    worker.postMessage.mockImplementation(() => {
      throw new Error('Worker gone');
    });
    surface!.dispose();
    expect(worker.terminate).toHaveBeenCalledOnce();
    expect(vi.getTimerCount()).toBe(0);
  });
});
