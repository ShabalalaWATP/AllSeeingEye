import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  discardResearchInput,
  geolocateResearchInput,
  type ResearchGeolocation,
} from '@/lib/api/researchGeolocation';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import { photoAssessment, photoReceipt } from '@/test/photoGeolocationFixture';

import { usePhotoGeolocation } from './usePhotoGeolocation';

vi.mock('@/lib/api/researchGeolocation', () => ({
  geolocateResearchInput: vi.fn(),
  discardResearchInput: vi.fn(),
}));
const analyse = vi.mocked(geolocateResearchInput);

describe('photo geolocation lifecycle guards', () => {
  beforeEach(() => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
    analyse.mockReset();
    vi.mocked(discardResearchInput).mockReset();
    vi.mocked(discardResearchInput).mockResolvedValue();
  });

  it('refuses missing consent and expired attachments before contacting a model', async () => {
    const expired = photoReceipt({ expires_at: new Date(Date.now() - 1000).toISOString() });
    const { result } = renderHook(() => usePhotoGeolocation(expired, 'private', ''));
    await act(() => result.current.analyse('Where?', '', false));
    expect(result.current.error).toBeNull();
    await act(() => result.current.analyse('Where?', '', true));
    expect(result.current.error).toContain('This photo has expired');
    expect(analyse).not.toHaveBeenCalled();
  });

  it('rejects an expired derived receipt returned by the server', async () => {
    analyse.mockResolvedValue(
      photoAssessment({
        input: photoReceipt({ expires_at: new Date(Date.now() - 1000).toISOString() }),
      }),
    );
    const receipt = photoReceipt();
    const { result } = renderHook(() => usePhotoGeolocation(receipt, 'private', ''));
    await act(() => result.current.analyse('Where?', '', true));
    expect(result.current.error).toContain('The analysis expired');
    expect(result.current.result).toBeNull();
  });

  it('allows only one model request at a time and drops late failures after cancellation', async () => {
    let fail: (error: Error) => void = () => undefined;
    analyse.mockImplementation(
      () =>
        new Promise((_resolve, reject) => {
          fail = reject;
        }),
    );
    const receipt = photoReceipt();
    const { result } = renderHook(() => usePhotoGeolocation(receipt, 'private', ''));
    let first: Promise<void>;
    act(() => {
      first = result.current.analyse('Where?', '', true);
    });
    await act(() => result.current.analyse('Where?', '', true));
    expect(analyse).toHaveBeenCalledTimes(1);
    act(() => result.current.clear('cancelled'));
    await act(async () => {
      fail(new Error('Late failure'));
      await first;
    });
    expect(result.current.status).toBe('cancelled');
    expect(result.current.error).toBeNull();
  });

  it('hides a result if a response arrives after the input has changed', async () => {
    let finish: (value: ResearchGeolocation) => void = () => undefined;
    analyse.mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const { result, rerender } = renderHook(
      ({ receipt }) => usePhotoGeolocation(receipt, 'private', ''),
      { initialProps: { receipt: photoReceipt() } },
    );
    act(() => {
      void result.current.analyse('Where?', '', true);
    });
    await waitFor(() => expect(analyse).toHaveBeenCalledTimes(1));
    rerender({ receipt: photoReceipt({ id: '10000000-0000-4000-8000-000000000099' }) });
    await act(async () => {
      finish(photoAssessment());
      await Promise.resolve();
    });
    expect(result.current.result).toBeNull();
    expect(analyse.mock.calls[0]?.[2].aborted).toBe(true);
  });

  it('discards only previous derived findings before reanalysis, even after editing its question', async () => {
    analyse.mockResolvedValue(photoAssessment());
    const receipt = photoReceipt();
    const { result } = renderHook(() => usePhotoGeolocation(receipt, 'private', ''));
    await act(() => result.current.analyse('Where?', '', true));
    act(() => result.current.clear());
    await act(() => result.current.analyse('Which city?', '', true));
    expect(discardResearchInput).toHaveBeenCalledWith(
      photoAssessment().input.id,
      expect.any(AbortSignal),
    );
    expect(analyse).toHaveBeenCalledTimes(2);
    expect(vi.mocked(discardResearchInput).mock.invocationCallOrder[0]).toBeLessThan(
      analyse.mock.invocationCallOrder[1]!,
    );
  });
});
