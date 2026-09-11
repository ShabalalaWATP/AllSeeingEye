import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';
import { discardResearchInput } from '@/lib/api/researchGeolocation';
import { uploadResearchInput } from '@/lib/api/researchInputs';
import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser, tokenFor } from '@/test/fixtures';
import { photoId, photoReceipt } from '@/test/photoGeolocationFixture';

import { usePhotoReplacement } from './usePhotoReplacement';
import { useResearchInput } from './useResearchInput';
import { holdPhotoReceipt } from './photoReceiptRegistry';

vi.mock('@/lib/api/researchGeolocation', () => ({ discardResearchInput: vi.fn() }));
vi.mock('@/lib/api/researchInputs', () => ({ uploadResearchInput: vi.fn() }));
const discard = vi.mocked(discardResearchInput);
const upload = vi.mocked(uploadResearchInput);
const file = () => new File(['photo'], 'landmark.jpg', { type: 'image/jpeg' });

function useHarness() {
  const input = useResearchInput(() => undefined);
  return { input, replacement: usePhotoReplacement(input) };
}

describe('explicit photo replacement', () => {
  beforeEach(() => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
    upload.mockReset();
    discard.mockReset();
    upload.mockResolvedValue(photoReceipt());
    discard.mockResolvedValue();
  });

  it('remembers a failed cleanup receipt and retries it before accepting another photo', async () => {
    const { result } = renderHook(useHarness);
    await act(() => result.current.input.upload(file()));
    discard.mockRejectedValueOnce(
      new ApiError(503, 'unavailable', 'Cleanup temporarily unavailable.'),
    );
    await act(() => result.current.replacement.replace(file()));
    expect(result.current.replacement.error).toBe('Cleanup temporarily unavailable.');
    expect(result.current.input.receipt).toBeNull();
    expect(upload).toHaveBeenCalledTimes(1);
    await act(() => result.current.replacement.replace(file()));
    expect(discard.mock.calls.map(([id]) => id)).toEqual([photoId, photoId]);
    expect(upload).toHaveBeenCalledTimes(2);
    expect(result.current.replacement.error).toBeNull();
  });

  it('does not begin a replacement upload after the active account changed during cleanup', async () => {
    let finish: () => void = () => undefined;
    discard.mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const { result } = renderHook(useHarness);
    await act(() => result.current.input.upload(file()));
    let task: Promise<boolean>;
    act(() => {
      task = result.current.replacement.replace(file());
    });
    await act(() => result.current.replacement.replace(file()));
    expect(discard).toHaveBeenCalledTimes(1);
    act(() => useAuthStore.getState().setSession(tokenFor(adminUser)));
    await act(async () => {
      finish();
      await task;
    });
    expect(discard.mock.calls[0]?.[1].aborted).toBe(true);
    expect(upload).toHaveBeenCalledTimes(1);
    expect(result.current.input.receipt).toBeNull();
  });

  it('does not discard receipts on ordinary unmount, when report persistence may still be using them', async () => {
    const { result, unmount } = renderHook(useHarness);
    await act(() => result.current.input.upload(file()));
    unmount();
    expect(discard).not.toHaveBeenCalled();
  });

  it('recovers outstanding references after leaving and returning to the page', async () => {
    const first = renderHook(useHarness);
    await act(() => first.result.current.input.upload(file()));
    first.unmount();
    const next = renderHook(useHarness);
    await act(() => next.result.current.replacement.replace(file()));
    expect(discard).toHaveBeenCalledWith(photoId, expect.any(AbortSignal));
    expect(upload).toHaveBeenCalledTimes(2);
  });

  it('keeps a pending report receipt until its request settles, then allows the next photo', async () => {
    const first = renderHook(useHarness);
    await act(() => first.result.current.input.upload(file()));
    const release = holdPhotoReceipt(
      first.result.current.input.key,
      first.result.current.input.receipt!,
    );
    first.unmount();
    const next = renderHook(useHarness);
    await act(() => next.result.current.replacement.replace(file()));
    expect(next.result.current.replacement.error).toContain('A photo report is still finishing');
    expect(discard).not.toHaveBeenCalled();
    expect(upload).toHaveBeenCalledTimes(1);
    release();
    await act(() => next.result.current.replacement.replace(file()));
    expect(discard).toHaveBeenCalledWith(photoId, expect.any(AbortSignal));
    expect(upload).toHaveBeenCalledTimes(2);
  });

  it('never reuses cleanup references after logout, even if the same account signs in again', async () => {
    const first = renderHook(useHarness);
    await act(() => first.result.current.input.upload(file()));
    first.unmount();
    useAuthStore.getState().clearSession();
    useAuthStore.getState().setSession(tokenFor(plainUser));
    const next = renderHook(useHarness);
    await act(() => next.result.current.replacement.replace(file()));
    expect(discard).not.toHaveBeenCalled();
    expect(upload).toHaveBeenCalledTimes(2);
  });
});
