import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { useEventsStore } from '@/stores/events';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { useLiveEvents } from './useLiveEvents';

vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

beforeEach(() => {
  vi.useFakeTimers();
  FakeEventStreamClient.reset();
  useEventsStore.getState().reset();
});

afterEach(() => {
  useEventsStore.getState().reset();
  FakeEventStreamClient.reset();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

it('loads exactly one initial snapshot when subscription succeeds', () => {
  const load = vi.spyOn(useEventsStore.getState(), 'load').mockResolvedValue();
  const { unmount } = renderHook(() => useLiveEvents());
  expect(load).toHaveBeenCalledOnce();
  act(() => {
    vi.advanceTimersByTime(10_000);
  });
  expect(load).toHaveBeenCalledOnce();
  unmount();
});

it('loads an offline snapshot after setup stalls, then reconciles when the stream connects', () => {
  FakeEventStreamClient.autoConnect = false;
  const load = vi.spyOn(useEventsStore.getState(), 'load').mockResolvedValue();
  const { unmount } = renderHook(() => useLiveEvents());
  expect(load).not.toHaveBeenCalled();
  act(() => {
    vi.advanceTimersByTime(2_999);
  });
  expect(load).not.toHaveBeenCalled();
  act(() => {
    vi.advanceTimersByTime(1);
  });
  expect(load).toHaveBeenCalledOnce();
  act(() => FakeEventStreamClient.instances[0]!.setStatus('live'));
  expect(load).toHaveBeenCalledTimes(2);
  unmount();
});

it('cancels the fallback when the view closes before connection', () => {
  FakeEventStreamClient.autoConnect = false;
  const load = vi.spyOn(useEventsStore.getState(), 'load').mockResolvedValue();
  const { unmount } = renderHook(() => useLiveEvents());
  unmount();
  act(() => {
    vi.advanceTimersByTime(10_000);
  });
  expect(load).not.toHaveBeenCalled();
  expect(FakeEventStreamClient.instances[0]!.stop).toHaveBeenCalledOnce();
});
