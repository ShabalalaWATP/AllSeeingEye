import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { useRfAutoUpdate } from './useRfAutoUpdate';
import { useAuthStore } from '@/stores/auth';
import { plainUser } from '@/test/fixtures';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(0);
  useAuthStore.setState({ user: plainUser, status: 'authenticated' });
});
afterEach(() => {
  vi.useRealTimers();
});
function fixture() {
  const run = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
  const cancel = vi.fn();
  const base = { identity: 'first', ready: true, busy: false, picking: false, run, cancel };
  return {
    ...renderHook((options) => useRfAutoUpdate(options), { initialProps: base }),
    base,
    run,
    cancel,
  };
}
async function advance(time: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(time);
  });
}
it('does no work on mount or edits until an explicit analysis and never polls unchanged inputs', async () => {
  const f = fixture();
  f.rerender({ ...f.base, identity: 'edited' });
  await advance(120000);
  expect(f.run).not.toHaveBeenCalled();
  act(() => f.result.current.manuallyAnalyse());
  expect(f.run).toHaveBeenCalledTimes(1);
  expect(f.result.current.armed).toBe(true);
  await advance(120000);
  expect(f.run).toHaveBeenCalledTimes(1);
});
it('coalesces edits, waits at least30seconds between attempts and uses the latest callback', async () => {
  const f = fixture();
  act(() => f.result.current.manuallyAnalyse());
  f.rerender({ ...f.base, identity: 'second' });
  await advance(29000);
  f.rerender({ ...f.base, identity: 'third' });
  await advance(1199);
  expect(f.run).toHaveBeenCalledTimes(1);
  const latest = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
  f.rerender({ ...f.base, identity: 'third', run: latest });
  await advance(1);
  expect(latest).toHaveBeenCalledTimes(1);
  f.rerender({ ...f.base, identity: 'fourth', run: latest });
  await advance(29999);
  expect(latest).toHaveBeenCalledTimes(1);
  await advance(1);
  expect(latest).toHaveBeenCalledTimes(2);
  await advance(120000);
  expect(latest).toHaveBeenCalledTimes(2);
});
it.each(['ready', 'busy', 'picking'] as const)(
  'pauses while %s blocks execution and resumes once valid',
  async (field) => {
    const f = fixture();
    const blocked = { ...f.base, [field]: field !== 'ready' };
    f.rerender(blocked);
    act(() => f.result.current.manuallyAnalyse());
    expect(f.run).not.toHaveBeenCalled();
    f.rerender(f.base);
    act(() => f.result.current.manuallyAnalyse());
    f.rerender({ ...blocked, identity: 'second' });
    await advance(60000);
    expect(f.run).toHaveBeenCalledTimes(1);
    f.rerender({ ...f.base, identity: 'second' });
    await advance(1199);
    expect(f.run).toHaveBeenCalledTimes(1);
    await advance(1);
    expect(f.run).toHaveBeenCalledTimes(2);
  },
);
it('supports opt-out, cancels automatic work and does not retry an already attempted identity', async () => {
  const f = fixture();
  act(() => f.result.current.manuallyAnalyse());
  f.rerender({ ...f.base, identity: 'second' });
  act(() => f.result.current.setEnabled(false));
  await advance(60000);
  expect(f.run).toHaveBeenCalledTimes(1);
  f.run.mockImplementation(() => new Promise(() => undefined));
  act(() => f.result.current.setEnabled(true));
  await advance(1200);
  expect(f.run).toHaveBeenCalledTimes(2);
  act(() => f.result.current.setEnabled(false));
  expect(f.cancel).toHaveBeenCalledTimes(1);
  act(() => f.result.current.setEnabled(true));
  await advance(60000);
  expect(f.run).toHaveBeenCalledTimes(2);
});
it('cancels and disarms onclear and only arms again with another explicit attempt', async () => {
  const f = fixture();
  act(() => f.result.current.manuallyAnalyse());
  f.rerender({ ...f.base, identity: 'second' });
  act(() => f.result.current.disarm());
  expect(f.cancel).toHaveBeenCalledTimes(1);
  expect(f.result.current.armed).toBe(false);
  await advance(60000);
  expect(f.run).toHaveBeenCalledTimes(1);
  act(() => f.result.current.manuallyAnalyse());
  expect(f.run).toHaveBeenCalledTimes(2);
});
it.each(['account', 'role', 'active', 'logout', 'access'] as const)(
  'disarms when %s changes',
  async (kind) => {
    const f = fixture();
    act(() => f.result.current.manuallyAnalyse());
    f.rerender({ ...f.base, identity: 'second' });
    act(() => {
      if (kind === 'access') invalidateWorkspaceAccess();
      else if (kind === 'logout') useAuthStore.setState({ user: null, status: 'anonymous' });
      else
        useAuthStore.setState({
          user: {
            ...plainUser,
            ...(kind === 'account'
              ? { id: 'another' }
              : kind === 'role'
                ? { role: 'admin' as const }
                : { is_active: false }),
          },
        });
    });
    expect(f.cancel).toHaveBeenCalledTimes(1);
    expect(f.result.current.armed).toBe(false);
    await advance(60000);
    expect(f.run).toHaveBeenCalledTimes(1);
  },
);
it('cancels pending work on unmount and does not inherit permission on reopening', async () => {
  const f = fixture();
  act(() => f.result.current.manuallyAnalyse());
  f.rerender({ ...f.base, identity: 'second' });
  f.unmount();
  expect(f.cancel).toHaveBeenCalledTimes(1);
  await advance(60000);
  expect(f.run).toHaveBeenCalledTimes(1);
  const reopened = fixture();
  expect(reopened.result.current.armed).toBe(false);
  await advance(60000);
  expect(reopened.run).not.toHaveBeenCalled();
});
