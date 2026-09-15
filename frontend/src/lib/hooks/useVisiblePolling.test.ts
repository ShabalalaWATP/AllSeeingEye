import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import { setVisibility } from '@/test/env';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';

import { useVisiblePolling, type PollOutcome } from './useVisiblePolling';

const advance = (ms: number) => act(() => vi.advanceTimersByTimeAsync(ms));

function start(poll: (signal: AbortSignal) => Promise<PollOutcome>, enabled = true) {
  return renderHook(
    ({ on }: { on: boolean }) => useVisiblePolling({ enabled: on, intervalMs: 30_000, poll }),
    { initialProps: { on: enabled } },
  );
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'Date'] });
  setVisibility('visible');
});

afterEach(() => {
  vi.useRealTimers();
});

it('polls on the interval while visible and pauses while hidden', async () => {
  const poll = vi.fn(() => Promise.resolve<PollOutcome>('ok'));
  start(poll);
  await advance(29_999);
  expect(poll).not.toHaveBeenCalled();
  await advance(1);
  expect(poll).toHaveBeenCalledTimes(1);
  act(() => setVisibility('hidden'));
  await advance(300_000);
  expect(poll).toHaveBeenCalledTimes(1);
});

it('refreshes at once on return when the last load is stale, otherwise waits out the interval', async () => {
  const poll = vi.fn(() => Promise.resolve<PollOutcome>('ok'));
  start(poll);
  act(() => setVisibility('hidden'));
  await advance(10_000);
  act(() => setVisibility('visible'));
  await advance(0);
  expect(poll).not.toHaveBeenCalled();
  await advance(20_000);
  expect(poll).toHaveBeenCalledTimes(1);
  act(() => setVisibility('hidden'));
  await advance(45_000);
  act(() => setVisibility('visible'));
  await advance(0);
  expect(poll).toHaveBeenCalledTimes(2);
});

it('never overlaps a request that is still in flight', async () => {
  let release: (value: PollOutcome) => void = () => undefined;
  const poll = vi.fn(
    () =>
      new Promise<PollOutcome>((resolve) => {
        release = resolve;
      }),
  );
  start(poll);
  await advance(30_000);
  expect(poll).toHaveBeenCalledTimes(1);
  act(() => setVisibility('hidden'));
  act(() => setVisibility('visible'));
  await advance(120_000);
  expect(poll).toHaveBeenCalledTimes(1);
  await act(async () => {
    release('ok');
    await Promise.resolve();
  });
  await advance(30_000);
  expect(poll).toHaveBeenCalledTimes(2);
});

it('doubles the delay after failures up to five minutes and resets after success', async () => {
  const outcomes: PollOutcome[] = ['failed', 'failed', 'failed', 'failed', 'failed', 'ok', 'ok'];
  const poll = vi.fn(() => {
    const next = outcomes.shift() ?? 'ok';
    return next === 'failed' ? Promise.reject(new Error('down')) : Promise.resolve(next);
  });
  start(poll);
  const times: number[] = [];
  let previous = Date.now();
  for (let call = 1; call <= 7; call += 1) {
    while (poll.mock.calls.length < call) await advance(1_000);
    times.push(Date.now() - previous);
    previous = Date.now();
  }
  expect(times).toEqual([30_000, 60_000, 120_000, 240_000, 300_000, 300_000, 30_000]);
});

it('keeps the current delay when a tick is skipped', async () => {
  const poll = vi
    .fn<() => Promise<PollOutcome>>()
    .mockResolvedValueOnce('failed')
    .mockResolvedValueOnce('skipped')
    .mockResolvedValue('ok');
  start(poll);
  await advance(30_000);
  await advance(60_000);
  expect(poll).toHaveBeenCalledTimes(2);
  await advance(59_999);
  expect(poll).toHaveBeenCalledTimes(2);
  await advance(1);
  expect(poll).toHaveBeenCalledTimes(3);
});

it('stops when the poll reports lost access and restarts only when re-enabled', async () => {
  const poll = vi.fn<() => Promise<PollOutcome>>().mockResolvedValueOnce('stop');
  poll.mockResolvedValue('ok');
  const view = start(poll);
  await advance(30_000);
  await advance(600_000);
  act(() => invalidateWorkspaceAccess());
  await advance(0);
  expect(poll).toHaveBeenCalledTimes(1);
  view.rerender({ on: false });
  view.rerender({ on: true });
  await advance(0);
  expect(poll).toHaveBeenCalledTimes(2);
});

it('does nothing while disabled', async () => {
  const poll = vi.fn(() => Promise.resolve<PollOutcome>('ok'));
  start(poll, false);
  await advance(600_000);
  expect(poll).not.toHaveBeenCalled();
});

it('checks immediately after an access change, aborting the stale request', async () => {
  const signals: AbortSignal[] = [];
  const poll = vi.fn(
    (signal: AbortSignal) =>
      new Promise<PollOutcome>((resolve) => {
        signals.push(signal);
        if (signals.length > 1) resolve('ok');
      }),
  );
  start(poll);
  await advance(30_000);
  act(() => invalidateWorkspaceAccess());
  await advance(0);
  expect(poll).toHaveBeenCalledTimes(2);
  expect(signals[0]?.aborted).toBe(true);
  expect(signals[1]?.aborted).toBe(false);
});

it('aborts in-flight work and clears timers on unmount', async () => {
  const signals: AbortSignal[] = [];
  const poll = vi.fn((signal: AbortSignal) => {
    signals.push(signal);
    return new Promise<PollOutcome>(() => undefined);
  });
  const view = start(poll);
  await advance(30_000);
  view.unmount();
  expect(signals[0]?.aborted).toBe(true);
  await advance(600_000);
  expect(poll).toHaveBeenCalledTimes(1);
});

it('measures staleness from an explicit load', async () => {
  const poll = vi.fn(() => Promise.resolve<PollOutcome>('ok'));
  const view = start(poll);
  await advance(25_000);
  act(() => setVisibility('hidden'));
  act(() => view.result.current.markLoaded());
  act(() => setVisibility('visible'));
  await advance(29_999);
  expect(poll).not.toHaveBeenCalled();
  await advance(1);
  expect(poll).toHaveBeenCalledTimes(1);
});
