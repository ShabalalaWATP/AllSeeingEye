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

function start(loader: () => Promise<string>) {
  return renderHook(() => usePolledResource(loader, INTERVAL));
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
