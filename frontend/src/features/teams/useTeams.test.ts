import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { useTeamAction, useTeamsResource } from './useTeams';

function pending<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

describe('team request lifetime', () => {
  it.each(['success', 'failure'])('discards a superseded %s response', async (outcome) => {
    const old = pending<string>();
    const first = () => old.promise;
    const next = () => Promise.resolve('current roster');
    const { result, rerender } = renderHook(({ loader }) => useTeamsResource(loader), {
      initialProps: { loader: first },
    });
    rerender({ loader: next });
    await waitFor(() => {
      expect(result.current.data).toBe('current roster');
    });
    await act(async () => {
      if (outcome === 'success') old.resolve('old roster');
      else old.reject(new Error('Old access denied'));
      await old.promise.catch(() => undefined);
    });
    expect(result.current.data).toBe('current roster');
    expect(result.current.error).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it('prevents a duplicate mutation before React renders the busy state', async () => {
    const request = pending<undefined>();
    const mutate = vi.fn(() => request.promise);
    const reload = vi.fn(() => Promise.resolve());
    const { result } = renderHook(useTeamAction);
    let completion: Promise<void> | undefined;
    act(() => {
      completion = result.current.run(mutate, 'Saved.', reload);
      void result.current.run(mutate, 'Saved.', reload);
    });
    expect(mutate).toHaveBeenCalledTimes(1);
    expect(result.current.busy).toBe(true);
    await act(async () => {
      request.resolve(undefined);
      await completion;
    });
    expect(reload).toHaveBeenCalledTimes(1);
    expect(result.current.busy).toBe(false);
    expect(result.current.notice).toBe('Saved.');
  });
});
