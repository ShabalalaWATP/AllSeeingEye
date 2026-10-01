import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';

import { resetVisibility, setVisibility } from '@/test/env';
import { jamMap } from '@/test/fixtures';
import { applySession } from '@/test/render';

const jam = vi.fn(() => Promise.resolve(jamMap));
vi.mock('@/lib/api/aviation', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/api/aviation')>()),
  fetchJamMap: () => jam(),
}));

const { useCyberWorkspace } = await import('./useCyberWorkspace');

beforeAll(() => applySession('user'));
afterEach(() => vi.useRealTimers());

describe('useCyberWorkspace', () => {
  afterEach(() => resetVisibility());

  it('refreshes the GNSS map on the timer only while the document is visible', async () => {
    vi.useFakeTimers();
    setVisibility('visible');
    renderHook(() => useCyberWorkspace(30));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });
    const initial = jam.mock.calls.length;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(299_000);
    });
    expect(jam.mock.calls.length).toBe(initial);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });
    expect(jam.mock.calls.length).toBe(initial + 1);
  });

  it('makes no requests while hidden and refreshes at once when an overdue tab returns', async () => {
    vi.useFakeTimers();
    setVisibility('visible');
    renderHook(() => useCyberWorkspace(30));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });
    const initial = jam.mock.calls.length;
    act(() => setVisibility('hidden'));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(600_000);
    });
    expect(jam.mock.calls.length).toBe(initial);
    act(() => setVisibility('visible'));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(jam.mock.calls.length).toBe(initial + 1);
  });

  it('waits out the rest of the interval when a tab returns before it is due', async () => {
    vi.useFakeTimers();
    setVisibility('visible');
    renderHook(() => useCyberWorkspace(30));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });
    const initial = jam.mock.calls.length;
    act(() => setVisibility('hidden'));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100_000);
    });
    act(() => setVisibility('visible'));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(jam.mock.calls.length).toBe(initial);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200_000);
    });
    expect(jam.mock.calls.length).toBe(initial + 1);
  });
});
