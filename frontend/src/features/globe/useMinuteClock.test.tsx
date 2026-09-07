import { act, renderHook } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { useMinuteClock } from './useMinuteClock';

afterEach(() => vi.useRealTimers());
it('updates on the next minute boundary and clears the pending timer on unmount', () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date('2026-09-07T12:00:41Z'));
  const view = renderHook(() => useMinuteClock());
  expect(new Date(view.result.current).toISOString()).toBe('2026-09-07T12:00:00.000Z');
  act(() => {
    vi.advanceTimersByTime(19_000);
  });
  expect(new Date(view.result.current).toISOString()).toBe('2026-09-07T12:01:00.000Z');
  view.unmount();
  expect(vi.getTimerCount()).toBe(0);
});
