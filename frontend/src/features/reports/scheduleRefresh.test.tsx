import { act, renderHook } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterEach, expect, it, vi } from 'vitest';

import { schedule } from '@/test/fixtures';
import { server } from '@/test/server';
import { useScheduleRefresh } from './useScheduleRefresh';

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

it('refreshes an idle subscription list after thirty seconds', async () => {
  let calls = 0;
  server.use(
    http.get('/api/schedules', () => {
      calls += 1;
      return HttpResponse.json({ items: [schedule] });
    }),
  );
  vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible');
  vi.useFakeTimers();
  const idle = [{ ...schedule, next_run_at: '2099-01-01T00:00:00Z' }];
  const setItems = vi.fn();
  renderHook(() => useScheduleRefresh(idle, 'owner', setItems));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(29_999);
  });
  expect(calls).toBe(0);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1);
  });
  expect(calls).toBe(1);
});

it('refreshes due subscriptions every five seconds and pauses while the page is hidden', async () => {
  let calls = 0;
  server.use(
    http.get('/api/schedules', () => {
      calls += 1;
      return HttpResponse.json({ items: [schedule] });
    }),
  );
  const visibility = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible');
  vi.useFakeTimers();
  const setItems = vi.fn();
  const due = [{ ...schedule, next_run_at: '2000-01-01T00:00:00Z' }];
  const { unmount } = renderHook(() => useScheduleRefresh(due, 'owner', setItems));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(4_999);
  });
  expect(calls).toBe(0);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1);
  });
  expect(calls).toBe(1);
  expect(setItems).toHaveBeenCalledTimes(1);
  visibility.mockReturnValue('hidden');
  document.dispatchEvent(new Event('visibilitychange'));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(120_000);
  });
  expect(calls).toBe(1);
  visibility.mockReturnValue('visible');
  await act(async () => {
    document.dispatchEvent(new Event('visibilitychange'));
    await Promise.resolve();
  });
  expect(calls).toBe(2);
  unmount();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(30_000);
  });
  expect(calls).toBe(2);
});

it('backs off after a refresh error while retaining the last list', async () => {
  let calls = 0;
  server.use(
    http.get('/api/schedules', () => {
      calls += 1;
      return calls === 1
        ? HttpResponse.json(
            { error: { code: 'unavailable', message: 'Refresh unavailable.' } },
            { status: 503 },
          )
        : HttpResponse.json({ items: [schedule] });
    }),
  );
  vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible');
  vi.useFakeTimers();
  const setItems = vi.fn();
  const due = [{ ...schedule, next_run_at: '2000-01-01T00:00:00Z' }];
  const { result } = renderHook(() => useScheduleRefresh(due, 'owner', setItems));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(5_000);
  });
  expect(calls).toBe(1);
  expect(result.current).toBe('Refresh unavailable.');
  expect(setItems).not.toHaveBeenCalled();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(9_999);
  });
  expect(calls).toBe(1);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1);
  });
  expect(calls).toBe(2);
  expect(result.current).toBeNull();
  expect(setItems).toHaveBeenCalledTimes(1);
});

it('hides a stale list when a refresh is permission denied', async () => {
  server.use(
    http.get('/api/schedules', () =>
      HttpResponse.json(
        { error: { code: 'forbidden', message: 'Subscription access changed.' } },
        { status: 403 },
      ),
    ),
  );
  vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible');
  vi.useFakeTimers();
  const setItems = vi.fn();
  const due = [{ ...schedule, next_run_at: '2000-01-01T00:00:00Z' }];
  const { result } = renderHook(() => useScheduleRefresh(due, 'owner', setItems));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(5_000);
  });
  expect(setItems).toHaveBeenCalledWith(null);
  expect(result.current).toBe('Subscription access changed.');
});

it('aborts an in-flight refresh when the list unmounts', async () => {
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let requestSignal: AbortSignal | null = null;
  server.use(
    http.get('/api/schedules', async ({ request }) => {
      requestSignal = request.signal;
      await gate;
      return HttpResponse.json({ items: [schedule] });
    }),
  );
  vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible');
  vi.useFakeTimers();
  const setItems = vi.fn();
  const due = [{ ...schedule, next_run_at: '2000-01-01T00:00:00Z' }];
  const { unmount } = renderHook(() => useScheduleRefresh(due, 'owner', setItems));
  await act(async () => vi.advanceTimersByTimeAsync(5_000));
  expect(requestSignal).not.toBeNull();
  unmount();
  expect((requestSignal as AbortSignal | null)?.aborted).toBe(true);
  await act(async () => {
    release();
    await gate;
  });
  expect(setItems).not.toHaveBeenCalled();
});
