import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { SnapshotRefresh, SNAPSHOT_REFRESH_MS, SNAPSHOT_COALESCE_MS } from './events.refresh';

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

it('coalesces invalidations and gives completed snapshots time to render', () => {
  const load = vi.fn();
  const refresh = new SnapshotRefresh(load);
  refresh.started();
  for (let i = 0; i < 100; i++) refresh.request(true);
  vi.advanceTimersByTime(15_000);
  expect(load).not.toHaveBeenCalled();
  refresh.finished();
  vi.advanceTimersByTime(SNAPSHOT_COALESCE_MS - 1);
  expect(load).not.toHaveBeenCalled();
  vi.advanceTimersByTime(1);
  expect(load).toHaveBeenCalledOnce();
  refresh.cancel();
});

it('paces refreshes and cancels queued work on navigation or logout', () => {
  const load = vi.fn();
  const refresh = new SnapshotRefresh(load);
  refresh.started();
  refresh.request(false);
  refresh.request(false);
  vi.advanceTimersByTime(SNAPSHOT_REFRESH_MS - 1);
  expect(load).not.toHaveBeenCalled();
  refresh.cancel();
  vi.advanceTimersByTime(SNAPSHOT_REFRESH_MS);
  expect(load).not.toHaveBeenCalled();
  refresh.request(false);
  vi.advanceTimersByTime(SNAPSHOT_COALESCE_MS);
  expect(load).toHaveBeenCalledOnce();
  refresh.started();
  refresh.finished();
  vi.advanceTimersByTime(SNAPSHOT_REFRESH_MS);
  expect(load).toHaveBeenCalledOnce();
});
