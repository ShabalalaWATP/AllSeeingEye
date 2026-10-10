import { act, render } from '@testing-library/react';
import { expect, it, vi } from 'vitest';

vi.unmock('./EvilEyeSurface');
const load = vi.hoisted(() => vi.fn());
vi.mock('./evilEyeLoader', () => ({ loadEyeRenderer: load }));
import EvilEyeSurface from './EvilEyeSurface';

it('retains the original capture without retrying when the fallback chunk cannot load', async () => {
  let reject!: (error: Error) => void;
  const pending = new Promise<never>((_, no) => {
    reject = no;
  });
  load.mockReturnValue(pending);
  vi.stubGlobal('Worker', undefined);
  const cancel = vi.fn();
  vi.stubGlobal('requestAnimationFrame', () => 1);
  vi.stubGlobal('cancelAnimationFrame', cancel);
  const view = render(<EvilEyeSurface workerRendering />);
  const gone = render(<EvilEyeSurface workerRendering />);
  gone.unmount();
  await act(async () => {
    reject(new Error('Synthetic missing renderer chunk'));
    await pending.catch(() => undefined);
  });
  expect(load).toHaveBeenCalled();
  expect(view.container.querySelector('img')).toBeVisible();
  expect(view.container.querySelector('canvas')).toBeNull();
  expect(cancel).toHaveBeenCalledWith(1);
  view.rerender(<EvilEyeSurface workerRendering paused />);
  view.rerender(<EvilEyeSurface workerRendering />);
  expect(view.container.querySelector('img')).toBeVisible();
  expect(view.container.querySelector('canvas')).toBeNull();
});
