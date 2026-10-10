import { describe, expect, it, vi } from 'vitest';

import { watchSessionRoute } from './sessionBootstrap';

function fixture(path = '/enterprise') {
  let notify: () => void = () => undefined;
  const unsubscribe = vi.fn();
  const router = {
    state: { matches: [{ route: { path } }] },
    subscribe: (listener: () => void) => {
      notify = listener;
      return unsubscribe;
    },
  };
  const bootstrap = vi.fn((): Promise<void> => Promise.resolve());
  let resolve!: (value: typeof bootstrap) => void;
  let reject!: (reason: Error) => void;
  const load = vi.fn(
    () =>
      new Promise<typeof bootstrap>((yes, no) => {
        resolve = yes;
        reject = no;
      }),
  );
  const reportFailure = vi.fn();
  const stop = () => watchSessionRoute(router, reportFailure, load);
  const visit = (next: string) => {
    router.state.matches = [{ route: { path: next } }];
    notify();
  };
  const ready = async () => {
    resolve(bootstrap);
    await Promise.resolve();
    await Promise.resolve();
  };
  const fail = async () => {
    reject(new Error('chunk unavailable'));
    await Promise.resolve();
    await Promise.resolve();
  };
  return { stop, ready, fail, visit, bootstrap, load, reportFailure, unsubscribe };
}

describe('session code loading', () => {
  it.each([
    '/enterprise',
    '/privacy',
    '/privacy/requests',
    '/attributions',
    '/accessibility',
    '/terms',
    '/business',
  ])('does not load account code on matched public route %s', (path) => {
    const f = fixture(path);
    f.stop();
    expect(f.load).not.toHaveBeenCalled();
    expect(f.bootstrap).not.toHaveBeenCalled();
  });

  it('loads once on private entry, then bootstraps once across navigation', async () => {
    const f = fixture();
    f.stop();
    f.visit('/login');
    f.visit('/request-account');
    expect(f.load).toHaveBeenCalledTimes(1);
    expect(f.bootstrap).not.toHaveBeenCalled();
    await f.ready();
    f.visit('/');
    expect(f.bootstrap).toHaveBeenCalledTimes(1);
    expect(f.load).toHaveBeenCalledTimes(1);
  });

  it('does not bootstrap a return to public while the chunk is loading', async () => {
    const f = fixture('/login');
    f.stop();
    f.visit('/enterprise');
    await f.ready();
    expect(f.bootstrap).not.toHaveBeenCalled();
    f.visit('/login');
    await f.ready();
    expect(f.bootstrap).toHaveBeenCalledTimes(1);
  });

  it('uses the current route if navigation returns to private during loading', async () => {
    const f = fixture('/login');
    f.stop();
    f.visit('/enterprise');
    f.visit('/login');
    await f.ready();
    expect(f.bootstrap).toHaveBeenCalledTimes(1);
  });

  it.each([false, true])('ignores %s rejection after cleanup', async (reject) => {
    const f = fixture('/login');
    const cleanup = f.stop();
    cleanup();
    if (reject) await f.fail();
    else await f.ready();
    expect(f.unsubscribe).toHaveBeenCalledTimes(1);
    expect(f.bootstrap).not.toHaveBeenCalled();
    expect(f.reportFailure).not.toHaveBeenCalled();
  });

  it('reports a failed chunk and clears the recovery message on public navigation', async () => {
    const f = fixture('/login');
    f.stop();
    await f.fail();
    expect(f.reportFailure).toHaveBeenLastCalledWith(true);
    expect(f.load).toHaveBeenCalledTimes(1);
    f.visit('/enterprise');
    expect(f.reportFailure).toHaveBeenLastCalledWith(false);
  });

  it('does not show a chunk failure after returning to a public page', async () => {
    const f = fixture('/login');
    f.stop();
    f.visit('/enterprise');
    await f.fail();
    expect(f.reportFailure).not.toHaveBeenCalledWith(true);
  });

  it('clears a failed import after a successful private-route retry', async () => {
    const f = fixture('/login');
    f.stop();
    await f.fail();
    expect(f.reportFailure).toHaveBeenLastCalledWith(true);
    f.visit('/request-account');
    await f.ready();
    await vi.waitFor(() => expect(f.reportFailure).toHaveBeenLastCalledWith(false));
    expect(f.bootstrap).toHaveBeenCalledTimes(1);
  });

  it.each([false, true])(
    'allows a bootstrap retry after rejection, with public return %s',
    async (publicReturn) => {
      const f = fixture('/login');
      f.bootstrap.mockRejectedValueOnce(new Error('session check failed'));
      f.stop();
      await f.ready();
      await vi.waitFor(() => expect(f.reportFailure).toHaveBeenLastCalledWith(true));
      if (publicReturn) f.visit('/enterprise');
      f.visit('/request-account');
      await f.ready();
      await vi.waitFor(() => expect(f.reportFailure).toHaveBeenLastCalledWith(false));
      expect(f.bootstrap).toHaveBeenCalledTimes(2);
    },
  );

  it('ignores an overlapping first import after StrictMode replaces its subscription', async () => {
    const first = fixture('/login');
    first.stop()();
    const second = fixture('/login');
    const cleanup = second.stop();
    await second.ready();
    await first.ready();
    expect(first.bootstrap).not.toHaveBeenCalled();
    expect(second.bootstrap).toHaveBeenCalledTimes(1);
    cleanup();
  });

  it('cancels the first subscription in a StrictMode setup-cleanup-setup cycle', async () => {
    const f = fixture('/login');
    f.stop()();
    await f.ready();
    const cleanup = f.stop();
    await f.ready();
    expect(f.bootstrap).toHaveBeenCalledTimes(1);
    cleanup();
  });
});
