import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { resetVisibility, setVisibility } from '@/test/env';
import { ukraineBoard } from '@/test/fixtures.ukraine';
import { ukraineDigest, ukraineDigestGenerating } from '@/test/fixtures.ukraineDigest';

import { REFRESH_MS, useUkraineBoard } from './useUkraineBoard';
import { DIGEST_POLL_MS, useUkraineDigest } from './useUkraineDigest';

const advance = (ms: number) => act(() => vi.advanceTimersByTimeAsync(ms));

beforeEach(() => {
  vi.useFakeTimers();
  setVisibility('visible');
});

afterEach(() => {
  vi.useRealTimers();
  resetVisibility();
});

describe('board refresh', () => {
  it('reloads on the interval while the document is visible', async () => {
    const load = vi.fn(() => Promise.resolve(ukraineBoard));
    const { result } = renderHook(() => useUkraineBoard(load));
    await advance(0);
    expect(load).toHaveBeenCalledTimes(1);
    expect(result.current.data?.board.day_number).toBe(1663);
    await advance(REFRESH_MS - 1);
    expect(load).toHaveBeenCalledTimes(1);
    await advance(1);
    expect(load).toHaveBeenCalledTimes(2);
  });

  it('makes no requests while hidden and refreshes at once when an overdue tab returns', async () => {
    const load = vi.fn(() => Promise.resolve(ukraineBoard));
    renderHook(() => useUkraineBoard(load));
    await advance(0);
    act(() => setVisibility('hidden'));
    await advance(REFRESH_MS * 3);
    expect(load).toHaveBeenCalledTimes(1);
    act(() => setVisibility('visible'));
    await advance(0);
    expect(load).toHaveBeenCalledTimes(2);
  });

  it('waits out the rest of the interval when a tab returns early', async () => {
    const load = vi.fn(() => Promise.resolve(ukraineBoard));
    renderHook(() => useUkraineBoard(load));
    await advance(0);
    act(() => setVisibility('hidden'));
    await advance(REFRESH_MS / 2);
    act(() => setVisibility('visible'));
    await advance(0);
    expect(load).toHaveBeenCalledTimes(1);
    await advance(REFRESH_MS / 2);
    expect(load).toHaveBeenCalledTimes(2);
  });
});

describe('digest polling', () => {
  it('does not poll once the digest is written', async () => {
    const load = vi.fn(() => Promise.resolve(ukraineDigest));
    renderHook(() => useUkraineDigest(load));
    await advance(0);
    await advance(DIGEST_POLL_MS * 4);
    expect(load).toHaveBeenCalledTimes(1);
  });

  it('pauses while hidden and checks at once when an overdue tab returns', async () => {
    const load = vi.fn(() => Promise.resolve(ukraineDigestGenerating));
    renderHook(() => useUkraineDigest(load));
    await advance(0);
    expect(load).toHaveBeenCalledTimes(1);
    await advance(DIGEST_POLL_MS);
    expect(load).toHaveBeenCalledTimes(2);
    act(() => setVisibility('hidden'));
    await advance(DIGEST_POLL_MS * 4);
    expect(load).toHaveBeenCalledTimes(2);
    act(() => setVisibility('visible'));
    await advance(0);
    expect(load).toHaveBeenCalledTimes(3);
  });

  it('stops polling when the digest finishes', async () => {
    const load = vi
      .fn<() => Promise<typeof ukraineDigest>>()
      .mockResolvedValueOnce(ukraineDigestGenerating)
      .mockResolvedValue(ukraineDigest);
    renderHook(() => useUkraineDigest(load));
    await advance(0);
    await advance(DIGEST_POLL_MS);
    expect(load).toHaveBeenCalledTimes(2);
    await advance(DIGEST_POLL_MS * 4);
    expect(load).toHaveBeenCalledTimes(2);
  });
});
