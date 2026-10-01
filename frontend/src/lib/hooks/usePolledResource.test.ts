import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { setVisibility } from '@/test/env';
import { plainUser, tokenFor } from '@/test/fixtures';

import { usePolledResource } from './usePolledResource';

const INTERVAL = 60_000;
const advance = (ms: number) => act(() => vi.advanceTimersByTimeAsync(ms));

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'Date'] });
  setVisibility('visible');
  useAuthStore.getState().setSession(tokenFor(plainUser));
});

afterEach(() => {
  vi.useRealTimers();
});

function start(loader: (signal: AbortSignal) => Promise<string>) {
  return renderHook(() => usePolledResource(loader, INTERVAL));
}

/** A loader whose requests stay open until released, rejecting like fetch once aborted. */
function controlledLoader() {
  const signals: AbortSignal[] = [];
  const releases: ((value: string) => void)[] = [];
  const loader = vi.fn(
    (signal: AbortSignal) =>
      new Promise<string>((resolve, reject) => {
        signals.push(signal);
        releases.push(resolve);
        signal.addEventListener('abort', () => {
          reject(new DOMException('The operation was aborted.', 'AbortError'));
        });
      }),
  );
  const release = (index: number, value: string) => releases[index]?.(value);
  return { loader, signals, release };
}

describe('polled shell resources', () => {
  it('loads at once, refreshes on the interval and keeps data on screen while refreshing', async () => {
    let round = 0;
    const loader = vi.fn(() => Promise.resolve(`round ${String(++round)}`));
    const view = start(loader);
    await advance(0);
    expect(view.result.current.data).toBe('round 1');
    await advance(INTERVAL);
    expect(loader).toHaveBeenCalledTimes(2);
    expect(view.result.current.data).toBe('round 2');
    expect(view.result.current.loading).toBe(false);
  });

  it('pauses while the tab is hidden and refreshes on return when the data is stale', async () => {
    const loader = vi.fn(() => Promise.resolve('alerts'));
    start(loader);
    await advance(0);
    act(() => setVisibility('hidden'));
    await advance(INTERVAL * 5);
    expect(loader).toHaveBeenCalledTimes(1);
    act(() => setVisibility('visible'));
    await advance(0);
    expect(loader).toHaveBeenCalledTimes(2);
  });

  it('backs off after a failed refresh and recovers after a success', async () => {
    const loader = vi
      .fn<() => Promise<string>>()
      .mockResolvedValueOnce('first')
      .mockRejectedValueOnce(new Error('down'))
      .mockResolvedValue('back');
    const view = start(loader);
    await advance(INTERVAL);
    expect(loader).toHaveBeenCalledTimes(2);
    expect(view.result.current.error).not.toBeNull();
    await advance(INTERVAL);
    expect(loader).toHaveBeenCalledTimes(2);
    await advance(INTERVAL);
    expect(loader).toHaveBeenCalledTimes(3);
    expect(view.result.current.data).toBe('back');
    await advance(INTERVAL);
    expect(loader).toHaveBeenCalledTimes(4);
  });

  it('reloads once after an access change instead of polling the stale scope too', async () => {
    const loader = vi.fn(() => Promise.resolve('scoped'));
    start(loader);
    await advance(0);
    act(() => invalidateWorkspaceAccess());
    await advance(0);
    expect(loader).toHaveBeenCalledTimes(2);
    await advance(INTERVAL - 1);
    expect(loader).toHaveBeenCalledTimes(2);
  });
});

describe('polled shell resources honour the abort signal', () => {
  it('passes a live signal to the loader and aborts it on unmount without updating state', async () => {
    const { loader, signals } = controlledLoader();
    const view = start(loader);
    await advance(0);
    expect(signals).toHaveLength(1);
    expect(signals[0]?.aborted).toBe(false);
    const errors = vi.spyOn(console, 'error');
    view.unmount();
    await advance(0);
    expect(signals[0]?.aborted).toBe(true);
    expect(errors).not.toHaveBeenCalled();
    errors.mockRestore();
  });

  it('aborts an in-flight refresh when the tab is hidden, keeping data and raising no error', async () => {
    const { loader, signals, release } = controlledLoader();
    const view = start(loader);
    await advance(0);
    release(0, 'first');
    await advance(0);
    await advance(INTERVAL);
    expect(signals).toHaveLength(2);
    act(() => setVisibility('hidden'));
    await advance(0);
    expect(signals[1]?.aborted).toBe(true);
    expect(view.result.current.data).toBe('first');
    expect(view.result.current.error).toBeNull();
    act(() => setVisibility('visible'));
    await advance(0);
    expect(signals).toHaveLength(3);
    release(2, 'second');
    await advance(0);
    expect(view.result.current.data).toBe('second');
  });

  it('aborts the stale request on an access change and never applies its answer', async () => {
    const { loader, signals, release } = controlledLoader();
    const view = start(loader);
    await advance(0);
    act(() => invalidateWorkspaceAccess());
    await advance(0);
    expect(signals[0]?.aborted).toBe(true);
    release(0, 'stale scope');
    const latest = signals.length - 1;
    expect(signals[latest]?.aborted).toBe(false);
    release(latest, 'fresh scope');
    await advance(0);
    expect(view.result.current.data).toBe('fresh scope');
    expect(view.result.current.error).toBeNull();
  });

  it('aborts an in-flight poll before a new load and does not back off for it', async () => {
    const { loader, signals, release } = controlledLoader();
    const view = start(loader);
    await advance(0);
    release(0, 'first');
    await advance(INTERVAL);
    expect(signals).toHaveLength(2);
    await act(async () => {
      const reload = view.result.current.reload();
      await Promise.resolve();
      expect(signals[1]?.aborted).toBe(true);
      release(2, 'manual');
      await reload;
    });
    expect(view.result.current.data).toBe('manual');
    expect(view.result.current.error).toBeNull();
    // The aborted poll is not a failure, so the next poll keeps the normal interval.
    await advance(INTERVAL);
    expect(signals).toHaveLength(4);
  });
});
