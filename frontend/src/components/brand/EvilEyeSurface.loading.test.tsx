import { act, render, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';

vi.unmock('./EvilEyeSurface');
const engine = vi.hoisted(() => ({
  load: vi.fn(),
  create: vi.fn(),
  render: vi.fn(),
  dispose: vi.fn(),
  resize: vi.fn(),
}));
const worker = vi.hoisted(() => ({ create: vi.fn() }));
vi.mock('./evilEyeLoader', () => ({ loadEyeRenderer: engine.load }));
vi.mock('./evilEyeWorkerClient', () => ({ createEyeWorker: worker.create }));
import EvilEyeSurface from './EvilEyeSurface';

beforeEach(() => worker.create.mockReset().mockReturnValue(null));

it('keeps the capture while loading and creates only the current, still-mounted surface', async () => {
  let ready!: () => void;
  const pending = new Promise<typeof engine.create>((resolve) => {
    ready = () => resolve(engine.create);
  });
  engine.load.mockReturnValue(pending);
  vi.stubGlobal('Worker', undefined);
  const frames = new Map<number, FrameRequestCallback>();
  let next = 0;
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
    frames.set(++next, callback);
    return next;
  });
  vi.stubGlobal('cancelAnimationFrame', (id: number) => frames.delete(id));
  engine.create.mockReturnValue({
    render: engine.render,
    dispose: engine.dispose,
    resize: engine.resize,
  });
  const gone = render(<EvilEyeSurface workerRendering />);
  expect(gone.container.querySelector('img')).toBeVisible();
  gone.unmount();
  const view = render(<EvilEyeSurface workerRendering eyeColor="#111111" />);
  view.rerender(<EvilEyeSurface workerRendering eyeColor="#222222" paused />);
  expect(view.container.querySelector('canvas')).toBeNull();
  expect(engine.create).not.toHaveBeenCalled();
  await act(async () => {
    ready();
    await pending;
  });
  await waitFor(() => expect(engine.create).toHaveBeenCalledTimes(1));
  expect(engine.create.mock.calls[0]?.[1]).toMatchObject({ eyeColor: '#222222' });
  expect(view.container.querySelector('canvas')).toBeInTheDocument();
  expect(view.container.querySelector('img')).toBeVisible();
  expect(frames.size).toBe(0);
  view.rerender(<EvilEyeSurface workerRendering eyeColor="#222222" />);
  const [id, callback] = [...frames.entries()][0]!;
  frames.delete(id);
  act(() => callback(1000));
  expect(engine.render).toHaveBeenCalledOnce();
  expect(view.container.querySelector('img')).not.toBeVisible();
  view.unmount();
  expect(engine.dispose).toHaveBeenCalledOnce();
  expect(frames.size).toBe(0);
});

it('replaces the worker canvas only after its fallback is loaded, ignoring stale startup failures', async () => {
  let ready!: () => void;
  let failed!: () => void;
  const pending = new Promise<typeof engine.create>((resolve) => {
    ready = () => resolve(engine.create);
  });
  engine.load.mockReturnValue(pending);
  const releaseWorker = vi.fn();
  worker.create.mockImplementation((_canvas, _options, _size, _rendered, fallback) => {
    failed = fallback;
    return { render: () => false, resize: vi.fn(), dispose: releaseWorker };
  });
  engine.create.mockReturnValue({
    render: engine.render,
    resize: engine.resize,
    dispose: engine.dispose,
  });
  const view = render(<EvilEyeSurface workerRendering paused />);
  const original = view.container.querySelector('canvas');
  expect(original).not.toBeNull();
  act(() => {
    failed();
    failed();
  });
  expect(engine.load).toHaveBeenCalledOnce();
  expect(engine.create).not.toHaveBeenCalled();
  expect(view.container.querySelector('img')).toBeVisible();
  await act(async () => {
    ready();
    await pending;
  });
  const replacement = view.container.querySelector('canvas');
  expect(replacement).not.toBe(original);
  expect(original).not.toBeInTheDocument();
  expect(engine.create.mock.calls[0]?.[0]).toBe(replacement);
  expect(releaseWorker).toHaveBeenCalledOnce();
  act(() => failed());
  expect(engine.create).toHaveBeenCalledOnce();
  view.unmount();
  expect(engine.dispose).toHaveBeenCalledOnce();
});
