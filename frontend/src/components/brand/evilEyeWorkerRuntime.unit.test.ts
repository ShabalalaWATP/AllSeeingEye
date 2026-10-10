import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { EyeOptions, EyeRequest } from './evilEyeProtocol';
import type { EyeWorkerScope } from './evilEyeWorkerRuntime';

const engine = vi.hoisted(() => ({
  create: vi.fn(),
  render: vi.fn(),
  resize: vi.fn(),
  dispose: vi.fn(),
}));
vi.mock('./evilEyeRenderer', () => ({ createEyeRenderer: engine.create }));
import { installEyeWorker } from './evilEyeWorkerRuntime';

beforeEach(() => {
  engine.create.mockReset().mockReturnValue(engine);
  engine.render.mockReset();
  engine.resize.mockReset();
  engine.dispose.mockReset();
});
function fixture() {
  const scope: EyeWorkerScope = { onmessage: null, postMessage: vi.fn() };
  installEyeWorker(scope);
  const send = (data: EyeRequest) => scope.onmessage?.({ data } as MessageEvent<EyeRequest>);
  const init: EyeRequest = {
    type: 'init',
    canvas: {} as OffscreenCanvas,
    options: {} as EyeOptions,
    noise: new Uint8Array([1, 2, 3, 4]),
    size: { width: 120, height: 60 },
  };
  return { scope, send, init };
}

describe('offscreen eye worker engine ownership', () => {
  it('passes the original inputs to the shared engine and acknowledges only completed frames', () => {
    const { scope, send, init } = fixture();
    send(init);
    expect(engine.create).toHaveBeenCalledWith(
      init.canvas,
      init.options,
      init.size,
      expect.any(Function),
      init.noise,
    );
    expect(scope.postMessage).toHaveBeenLastCalledWith({ type: 'ready' });
    send({ type: 'resize', size: { width: 240, height: 120 } });
    expect(engine.resize).toHaveBeenCalledWith({ width: 240, height: 120 });
    const frame = { time: 123456, mouse: [0.05, -0.05] as [number, number] };
    send({ type: 'frame', frame });
    expect(engine.render).toHaveBeenCalledWith(frame);
    expect(scope.postMessage).toHaveBeenLastCalledWith({ type: 'frame' });
    send({ type: 'dispose' });
    expect(engine.dispose).toHaveBeenCalledOnce();
    expect(scope.postMessage).toHaveBeenLastCalledWith({ type: 'disposed' });
    send(init);
    send({ type: 'frame', frame });
    expect(engine.create).toHaveBeenCalledOnce();
    expect(engine.render).toHaveBeenCalledOnce();
  });

  it('reports startup failures without exposing details', () => {
    engine.create.mockImplementation(() => {
      throw new Error('Driver details');
    });
    const { scope, send, init } = fixture();
    send(init);
    expect(scope.postMessage).toHaveBeenCalledExactlyOnceWith({ type: 'failed', phase: 'startup' });
    send(init);
    expect(engine.create).toHaveBeenCalledOnce();
  });

  it.each(['render', 'lost'] as const)(
    'makes %s failure terminal and releases the engine',
    (reason) => {
      const { scope, send, init } = fixture();
      send(init);
      if (reason === 'render') {
        engine.render.mockImplementation(() => {
          throw new Error('GPU reset');
        });
        send({ type: 'frame', frame: { time: 1000, mouse: [0, 0] } });
      } else {
        const onLost = engine.create.mock.calls[0]![3] as () => void;
        onLost();
      }
      expect(engine.dispose).toHaveBeenCalledOnce();
      expect(scope.postMessage).toHaveBeenLastCalledWith({ type: 'failed', phase: reason });
      send(init);
      expect(engine.create).toHaveBeenCalledOnce();
      expect(scope.postMessage).not.toHaveBeenCalledWith({ type: 'frame' });
    },
  );
});
