import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';

import { useConfirmedAction } from './useConfirmedAction';

function deferred() {
  let resolve: () => void = () => undefined;
  let reject: (reason: unknown) => void = () => undefined;
  const promise = new Promise<void>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}

describe('useConfirmedAction', () => {
  it('sends nothing until the request is confirmed, and nothing when cancelled', () => {
    const action = vi.fn(() => Promise.resolve());
    const { result } = renderHook(() => useConfirmedAction(action));
    act(() => {
      result.current.ask('report-1');
    });
    expect(result.current.target).toBe('report-1');
    expect(action).not.toHaveBeenCalled();
    act(() => {
      result.current.cancel();
    });
    expect(result.current.target).toBeNull();
    expect(action).not.toHaveBeenCalled();
  });

  it('sends one request however often it is confirmed, then closes on success', async () => {
    const pending = deferred();
    const action = vi.fn(() => pending.promise);
    const { result } = renderHook(() => useConfirmedAction(action));
    act(() => {
      result.current.ask('rule-1');
    });
    act(() => {
      result.current.confirm();
      result.current.confirm();
    });
    expect(result.current.busy).toBe(true);
    act(() => {
      result.current.confirm();
      result.current.cancel();
    });
    expect(action).toHaveBeenCalledTimes(1);
    expect(action).toHaveBeenCalledWith('rule-1');
    expect(result.current.target).toBe('rule-1');
    await act(async () => {
      pending.resolve();
      await pending.promise;
    });
    expect(result.current.busy).toBe(false);
    expect(result.current.target).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('keeps the request open with a normalised error so it can be retried', async () => {
    const action = vi
      .fn<(target: string) => Promise<void>>()
      .mockRejectedValueOnce(new ApiError(403, 'forbidden', 'Not allowed.'))
      .mockResolvedValueOnce(undefined);
    const { result } = renderHook(() => useConfirmedAction(action));
    act(() => {
      result.current.ask('user-1');
    });
    await act(async () => {
      result.current.confirm();
      await Promise.resolve();
    });
    expect(result.current.target).toBe('user-1');
    expect(result.current.error?.status).toBe(403);
    await act(async () => {
      result.current.confirm();
      await Promise.resolve();
    });
    expect(action).toHaveBeenCalledTimes(2);
    expect(result.current.target).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('clears an earlier failure when a new request is asked or cancelled', async () => {
    const action = vi.fn(() => Promise.reject(new Error('offline')));
    const { result } = renderHook(() => useConfirmedAction(action));
    act(() => {
      result.current.ask('area-1');
    });
    await act(async () => {
      result.current.confirm();
      await Promise.resolve();
    });
    expect(result.current.error).not.toBeNull();
    act(() => {
      result.current.cancel();
    });
    expect(result.current.error).toBeNull();
    act(() => {
      result.current.ask('area-2');
    });
    expect(result.current.error).toBeNull();
    expect(result.current.target).toBe('area-2');
  });

  it('ignores a confirmation when nothing was asked', () => {
    const action = vi.fn(() => Promise.resolve());
    const { result } = renderHook(() => useConfirmedAction(action));
    act(() => {
      result.current.confirm();
    });
    expect(action).not.toHaveBeenCalled();
  });
});
