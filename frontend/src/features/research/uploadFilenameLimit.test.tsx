/** KAN-208: a filename the server would refuse is explained before any bytes are sent. */
import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { uploadResearchInput } from '@/lib/api/researchInputs';
import { inputFilenameError, MAX_INPUT_FILENAME_LENGTH } from '@/lib/uploadFilename';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import { photoReceipt } from '@/test/photoGeolocationFixture';

import { usePhotoInputs } from './usePhotoInputs';
import { useResearchInput } from './useResearchInput';

vi.mock('@/lib/api/researchInputs', async (original) => ({
  ...(await original<typeof import('@/lib/api/researchInputs')>()),
  uploadResearchInput: vi.fn(),
}));
const upload = vi.mocked(uploadResearchInput);
const RENAME = 'Rename the file to 120 characters or fewer, then choose it again.';
const named = (stem: string, extension: string) =>
  new File(['bytes'], `${stem}${extension}`, { type: 'application/octet-stream' });

beforeEach(() => {
  useAuthStore.getState().setSession(tokenFor(plainUser));
  upload.mockReset();
  upload.mockResolvedValue(photoReceipt());
});

describe('inputFilenameError', () => {
  it('accepts names up to the limit and explains longer ones', () => {
    expect(inputFilenameError('a'.repeat(MAX_INPUT_FILENAME_LENGTH))).toBeNull();
    expect(inputFilenameError('a'.repeat(MAX_INPUT_FILENAME_LENGTH + 1))).toBe(RENAME);
  });

  it('counts characters as the server does, not UTF-16 units', () => {
    // Each emoji is one character but two UTF-16 units.
    expect(inputFilenameError(`${'😀'.repeat(100)}.png`)).toBeNull();
    expect(inputFilenameError(`${'😀'.repeat(117)}.png`)).toBe(RENAME);
  });
});

describe('research input upload', () => {
  it('refuses a long filename without uploading it', async () => {
    const onChange = vi.fn();
    const { result } = renderHook(() => useResearchInput(onChange));
    await act(() => result.current.upload(named('r'.repeat(117), '.pdf')));
    expect(result.current.status).toBe('error');
    expect(result.current.error).toBe(RENAME);
    expect(upload).not.toHaveBeenCalled();
  });

  it('still uploads a filename exactly at the limit', async () => {
    const { result } = renderHook(() => useResearchInput(vi.fn()));
    await act(() => result.current.upload(named('r'.repeat(116), '.pdf')));
    expect(upload).toHaveBeenCalledOnce();
  });
});

describe('photo batch upload', () => {
  it('refuses a batch containing a long filename and keeps the current state', async () => {
    const { result } = renderHook(usePhotoInputs);
    let accepted = true;
    await act(async () => {
      accepted = await result.current.replace([
        named('short', '.jpg'),
        named('p'.repeat(117), '.jpg'),
      ]);
    });
    expect(accepted).toBe(false);
    expect(result.current.error).toBe(RENAME);
    expect(result.current.status).toBe('idle');
    expect(upload).not.toHaveBeenCalled();
  });
});
