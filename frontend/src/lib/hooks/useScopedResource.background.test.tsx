import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';

import { useScopedResource } from './useScopedResource';

const offline = new ApiError(503, 'unavailable', 'Try later.');

describe('Scoped resource background refresh', () => {
  it('keeps visible data when a background refresh fails and clears the error on recovery', async () => {
    const loader = vi
      .fn<() => Promise<string>>()
      .mockResolvedValueOnce('three alerts')
      .mockRejectedValueOnce(offline)
      .mockResolvedValueOnce('four alerts');
    const { result } = renderHook(() => useScopedResource(loader));
    await waitFor(() => expect(result.current.data).toBe('three alerts'));

    await act(() => result.current.refresh());
    expect(result.current).toMatchObject({ data: 'three alerts', error: offline, loading: false });

    await act(() => result.current.refresh());
    expect(result.current).toMatchObject({ data: 'four alerts', error: null, loading: false });
  });

  it('keeps an error on screen instead of a spinner while refreshing in the background', async () => {
    let finish!: (value: string) => void;
    const loader = vi
      .fn<() => Promise<string>>()
      .mockRejectedValueOnce(offline)
      .mockReturnValueOnce(
        new Promise<string>((resolve) => {
          finish = resolve;
        }),
      );
    const { result } = renderHook(() => useScopedResource(loader));
    await waitFor(() => expect(result.current.error).toBe(offline));

    let pending!: Promise<void>;
    act(() => {
      pending = result.current.refresh();
    });
    expect(result.current).toMatchObject({ data: null, error: offline, loading: false });
    await act(async () => {
      finish('recovered');
      await pending;
    });
    expect(result.current).toMatchObject({ data: 'recovered', error: null, loading: false });
  });

  it('still starts again from a loading state on an explicit reload', async () => {
    let finish!: (value: string) => void;
    const loader = vi
      .fn<() => Promise<string>>()
      .mockResolvedValueOnce('first')
      .mockReturnValueOnce(
        new Promise<string>((resolve) => {
          finish = resolve;
        }),
      );
    const { result } = renderHook(() => useScopedResource(loader));
    await waitFor(() => expect(result.current.data).toBe('first'));

    let pending!: Promise<void>;
    act(() => {
      pending = result.current.reload();
    });
    expect(result.current).toMatchObject({ data: null, loading: true });
    await act(async () => {
      finish('second');
      await pending;
    });
    expect(result.current.data).toBe('second');
  });

  it('does not keep data from a failed first load', async () => {
    const loader = vi.fn<() => Promise<string>>().mockRejectedValue(offline);
    const { result } = renderHook(() => useScopedResource(loader));
    await waitFor(() => expect(result.current.error).toBe(offline));
    await act(() => result.current.refresh());
    expect(result.current).toMatchObject({ data: null, error: offline, loading: false });
  });
});
