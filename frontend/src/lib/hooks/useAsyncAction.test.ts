import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { useAsyncAction } from './useAsyncAction';

function deferred() {
  let resolve: () => void = () => undefined;
  let reject: (reason: unknown) => void = () => undefined;
  const promise = new Promise<void>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}

describe('useAsyncAction', () => {
  it('ignores a second run while the first is still pending', async () => {
    const gate = deferred();
    const action = vi.fn(() => gate.promise);
    const { result } = renderHook(() => useAsyncAction(action));

    let first: Promise<void> = Promise.resolve();
    let second: Promise<void> = Promise.resolve();
    act(() => {
      // Both calls happen before React commits the busy render.
      first = result.current.run();
      second = result.current.run();
    });
    expect(action).toHaveBeenCalledTimes(1);
    expect(result.current.busy).toBe(true);

    await act(async () => {
      gate.resolve();
      await Promise.all([first, second]);
    });
    expect(action).toHaveBeenCalledTimes(1);
    expect(result.current.busy).toBe(false);
  });

  it('runs again once the previous attempt has settled', async () => {
    const action = vi.fn<(value: number) => Promise<void>>(() => Promise.resolve());
    const { result } = renderHook(() => useAsyncAction(action));
    await act(() => result.current.run(1));
    await act(() => result.current.run(2));
    expect(action.mock.calls).toEqual([[1], [2]]);
  });

  it('releases the guard after a failure and reports the error', async () => {
    const gate = deferred();
    const action = vi.fn(() => gate.promise);
    const { result } = renderHook(() => useAsyncAction(action));
    let first: Promise<void> = Promise.resolve();
    act(() => {
      first = result.current.run();
    });
    await act(async () => {
      gate.reject(new Error('Network down'));
      await first;
    });
    expect(result.current.error).not.toBeNull();
    expect(result.current.busy).toBe(false);

    action.mockResolvedValueOnce(undefined);
    await act(() => result.current.run());
    expect(action).toHaveBeenCalledTimes(2);
    expect(result.current.error).toBeNull();
  });
});
