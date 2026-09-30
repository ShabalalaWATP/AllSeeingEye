import { act, renderHook } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { ApiError } from '@/lib/api/errors';
import { discardResearchInput } from '@/lib/api/researchGeolocation';
import { uploadResearchInput, type ResearchInputReceipt } from '@/lib/api/researchInputs';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import { photoReceipt } from '@/test/photoGeolocationFixture';
import { usePhotoInputs } from './usePhotoInputs';

vi.mock('@/lib/api/researchGeolocation', () => ({ discardResearchInput: vi.fn() }));
vi.mock('@/lib/api/researchInputs', () => ({ uploadResearchInput: vi.fn() }));
const upload = vi.mocked(uploadResearchInput);
const discard = vi.mocked(discardResearchInput);
const photo = () => new File(['pixels'], 'photo.jpg', { type: 'image/jpeg' });

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (value: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

beforeEach(() => {
  useAuthStore.getState().setSession(tokenFor(plainUser));
  upload.mockReset();
  discard.mockReset().mockResolvedValue();
});

it('rejects a second batch while uploading and ignores a late failure after cancellation', async () => {
  const pending = deferred<ResearchInputReceipt>();
  upload.mockReturnValue(pending.promise);
  const { result } = renderHook(usePhotoInputs);
  let first!: Promise<boolean>;
  act(() => {
    first = result.current.replace([photo()]);
  });
  await act(async () => expect(await result.current.replace([photo()])).toBe(false));
  expect(upload).toHaveBeenCalledTimes(1);
  act(() => result.current.clear('cancelled'));
  expect(upload.mock.calls[0]![1].aborted).toBe(true);
  await act(async () => {
    pending.reject(new Error('Late failure'));
    expect(await first).toBe(false);
  });
  expect(result.current.status).toBe('cancelled');
  expect(result.current.error).toBeNull();
});

it('stops replacing after a pending discard when workspace access changes', async () => {
  const pending = deferred<undefined>();
  upload.mockResolvedValue(photoReceipt());
  const { result } = renderHook(usePhotoInputs);
  await act(() => result.current.replace([photo()]));
  discard.mockReturnValue(pending.promise);
  let replacing!: Promise<boolean>;
  act(() => {
    replacing = result.current.replace([photo()]);
  });
  act(() => invalidateWorkspaceAccess());
  await act(async () => {
    pending.resolve(undefined);
    expect(await replacing).toBe(false);
  });
  expect(upload).toHaveBeenCalledTimes(1);
  expect(result.current.receipts).toEqual([]);
  expect(result.current.status).toBe('idle');
});

it('drops an upload completed after logout, including its outstanding receipt', async () => {
  const pending = deferred<ResearchInputReceipt>();
  upload.mockReturnValue(pending.promise);
  const { result } = renderHook(usePhotoInputs);
  let first!: Promise<boolean>;
  act(() => {
    first = result.current.replace([photo()]);
  });
  act(() => useAuthStore.getState().clearSession());
  await act(async () => {
    pending.resolve(photoReceipt());
    expect(await first).toBe(false);
  });
  expect(result.current.receipts).toEqual([]);
  expect(result.current.status).toBe('idle');
  act(() => useAuthStore.getState().setSession(tokenFor(plainUser)));
  upload.mockResolvedValue(photoReceipt());
  await act(() => result.current.replace([photo()]));
  expect(discard).not.toHaveBeenCalled();
});

it('refuses receipts that expire in transit and removes an accepted receipt back to idle', async () => {
  upload.mockResolvedValueOnce(
    photoReceipt({ expires_at: new Date(Date.now() - 1000).toISOString() }),
  );
  const { result } = renderHook(usePhotoInputs);
  await act(async () => expect(await result.current.replace([photo()])).toBe(false));
  expect(result.current.status).toBe('expired');
  expect(result.current.receipts).toEqual([]);
  upload.mockResolvedValueOnce(photoReceipt());
  await act(() => result.current.replace([photo()]));
  await act(() => result.current.remove(photoReceipt().id));
  expect(discard).toHaveBeenCalledWith(photoReceipt().id, expect.any(AbortSignal));
  expect(result.current.status).toBe('idle');
  expect(result.current.receipts).toEqual([]);
});

it('explains temporary upload limits and allows retry after the failed batch', async () => {
  upload.mockRejectedValueOnce(new ApiError(429, 'rate_limited', 'Upload limit reached.'));
  const { result } = renderHook(usePhotoInputs);
  await act(async () => expect(await result.current.replace([photo()])).toBe(false));
  expect(result.current.status).toBe('error');
  expect(result.current.error).toContain('Remove unused photos or wait for temporary uploads');
  upload.mockResolvedValueOnce(photoReceipt());
  await act(async () => expect(await result.current.replace([photo()])).toBe(true));
  expect(result.current.status).toBe('ready');
  expect(result.current.error).toBeNull();
});
