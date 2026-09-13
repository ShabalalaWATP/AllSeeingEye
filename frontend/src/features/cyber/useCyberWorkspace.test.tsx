import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';

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
  it('refreshes the GNSS map on the timer only while the document is visible', async () => {
    vi.useFakeTimers();
    renderHook(() => useCyberWorkspace(30));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });
    const initial = jam.mock.calls.length;
    const visibility = vi.spyOn(document, 'visibilityState', 'get');
    visibility.mockReturnValue('hidden');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300_000);
    });
    expect(jam.mock.calls.length).toBe(initial);
    visibility.mockReturnValue('visible');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300_000);
    });
    expect(jam.mock.calls.length).toBeGreaterThan(initial);
    visibility.mockRestore();
  });
});
