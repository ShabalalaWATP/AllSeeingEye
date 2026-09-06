import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';
import { uploadResearchInput } from '@/lib/api/researchInputs';
import type { ResearchInputReceipt } from '@/lib/api/researchInputs';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser, tokenFor } from '@/test/fixtures';

import { ResearchInput } from './ResearchInput';
import { MAX_IMPORT_BYTES } from './useResearchInput';

vi.mock('@/lib/api/researchInputs', () => ({ uploadResearchInput: vi.fn() }));
const upload = vi.mocked(uploadResearchInput);

function receipt(overrides: Partial<ResearchInputReceipt> = {}): ResearchInputReceipt {
  return {
    id: '10000000-0000-4000-8000-000000000001',
    filename: 'notes.txt',
    media_type: 'text/plain',
    sha256: 'a'.repeat(64),
    imported_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 15 * 60_000).toISOString(),
    event_count: 2,
    extracted_characters: 123,
    preview: '<script>claim</script>',
    limitations: ['Original publication date is unknown.'],
    previews: [],
    ...overrides,
  };
}

function choose(file = new File(['source'], 'notes.txt', { type: 'text/plain' })) {
  fireEvent.change(screen.getByLabelText('Document or media'), { target: { files: [file] } });
}

describe('private research attachment', () => {
  beforeEach(() => {
    upload.mockReset();
    useAuthStore.getState().setSession(tokenFor(plainUser));
  });
  afterEach(() => vi.useRealTimers());

  it('uploads one file, exposes its id and renders extracted source text without HTML', async () => {
    upload.mockResolvedValue(receipt());
    const changed = vi.fn();
    const busy = vi.fn();
    const { container } = render(<ResearchInput onChange={changed} onBusyChange={busy} />);
    expect(screen.getByLabelText('Document or media')).toHaveAttribute(
      'accept',
      expect.stringContaining('.webm'),
    );
    choose();
    expect(await screen.findByText('Attached: notes.txt')).toBeVisible();
    expect(changed).toHaveBeenLastCalledWith('10000000-0000-4000-8000-000000000001');
    // The parent notification runs in an effect after the receipt is rendered.
    await waitFor(() => expect(busy).toHaveBeenLastCalledWith(false));
    fireEvent.click(screen.getByText('Extraction preview and limitations'));
    expect(screen.getByText('<script>claim</script>')).toBeVisible();
    expect(container.querySelector('script')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Remove attachment' }));
    expect(screen.queryByText('Attached: notes.txt')).not.toBeInTheDocument();
    expect(changed).toHaveBeenLastCalledWith(null);
  });

  it('shows sanitised PNG previews and video sample times', async () => {
    upload.mockResolvedValue(
      receipt({
        filename: 'clip.mp4',
        media_type: 'video/mp4',
        previews: [{ seconds: 12.3, sha256: 'b'.repeat(64), png_base64: 'iVBORw0KGgo=' }],
      }),
    );
    render(<ResearchInput onChange={vi.fn()} />);
    choose(new File(['clip'], 'clip.mp4'));
    const preview = await screen.findByRole('img', { name: 'Sanitised preview 1 of clip.mp4' });
    expect(preview).toHaveAttribute('src', 'data:image/png;base64,iVBORw0KGgo=');
    expect(screen.getByText('Frame at 12.3 seconds')).toBeVisible();
  });

  it('explains an image preview when no text was extracted', async () => {
    upload.mockResolvedValue(
      receipt({
        filename: 'image.png',
        media_type: 'image/png',
        preview: '',
        previews: [{ seconds: 0, sha256: 'b'.repeat(64), png_base64: 'iVBORw0KGgo=' }],
      }),
    );
    render(<ResearchInput onChange={vi.fn()} />);
    choose(new File(['image'], 'image.png'));
    await screen.findByRole('img');
    expect(screen.getByText('Resized, metadata-stripped preview')).toBeVisible();
    fireEvent.click(screen.getByText('Extraction preview and limitations'));
    expect(screen.getByText('No text preview available.')).toBeVisible();
  });

  it('does nothing when a file picker closes without a selection', () => {
    render(<ResearchInput onChange={vi.fn()} />);
    fireEvent.change(screen.getByLabelText('Document or media'), { target: { files: null } });
    expect(upload).not.toHaveBeenCalled();
  });

  it('accepts a document receipt without the optional media preview field', async () => {
    const value = receipt();
    delete value.previews;
    upload.mockResolvedValue(value);
    render(<ResearchInput onChange={vi.fn()} />);
    choose();
    await screen.findByText('Attached: notes.txt');
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });

  it('drops late failures when logout clears an in-flight private upload', async () => {
    let fail: (error: Error) => void = () => undefined;
    upload.mockImplementation(
      () =>
        new Promise((_resolve, reject) => {
          fail = reject;
        }),
    );
    const changed = vi.fn();
    render(<ResearchInput onChange={changed} />);
    choose();
    act(() => useAuthStore.getState().clearSession());
    await act(async () => {
      fail(new Error('Late response'));
      await Promise.resolve();
    });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.queryByText(/Uploading and extracting/)).not.toBeInTheDocument();
    expect(changed).toHaveBeenLastCalledWith(null);
  });

  it('aborts an upload and ignores a response arriving after cancellation', async () => {
    let finish: (value: ResearchInputReceipt) => void = () => undefined;
    upload.mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const changed = vi.fn();
    render(<ResearchInput onChange={changed} />);
    choose();
    expect(screen.getByText('Uploading and extracting notes.txt…')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Cancel import' }));
    expect(upload.mock.calls[0]?.[1].aborted).toBe(true);
    await act(async () => {
      finish(receipt());
      await Promise.resolve();
    });
    expect(screen.getByText('Import cancelled.')).toBeVisible();
    expect(screen.queryByText('Attached: notes.txt')).not.toBeInTheDocument();
    expect(changed).toHaveBeenLastCalledWith(null);
  });

  it('replaces previous evidence immediately and never restores a slow prior upload', async () => {
    let finish: (value: ResearchInputReceipt) => void = () => undefined;
    upload.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    upload.mockResolvedValueOnce(receipt({ filename: 'replacement.csv' }));
    render(<ResearchInput onChange={vi.fn()} />);
    choose();
    choose(new File(['a,b'], 'replacement.csv'));
    expect(await screen.findByText('Attached: replacement.csv')).toBeVisible();
    await act(async () => {
      finish(receipt());
      await Promise.resolve();
    });
    expect(screen.queryByText('Attached: notes.txt')).not.toBeInTheDocument();
    expect(upload.mock.calls[0]?.[1].aborted).toBe(true);
  });

  it.each(['account', 'workspace'] as const)(
    'hides private previews on %s changes',
    async (change) => {
      upload.mockResolvedValue(receipt());
      const changed = vi.fn();
      render(<ResearchInput onChange={changed} />);
      choose();
      await screen.findByText('Attached: notes.txt');
      act(() => {
        if (change === 'account') useAuthStore.getState().setSession(tokenFor(adminUser));
        else invalidateWorkspaceAccess();
      });
      expect(screen.queryByText('Attached: notes.txt')).not.toBeInTheDocument();
      expect(changed).toHaveBeenLastCalledWith(null);
    },
  );

  it('clears the parent id when evidence expires', async () => {
    vi.useFakeTimers();
    upload.mockResolvedValue(receipt({ expires_at: new Date(Date.now() + 1000).toISOString() }));
    const changed = vi.fn();
    render(<ResearchInput onChange={changed} />);
    choose();
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByText('Attached: notes.txt')).toBeVisible();
    act(() => {
      vi.advanceTimersByTime(1001);
    });
    expect(screen.getByText(/This attachment has expired/)).toBeVisible();
    expect(changed).toHaveBeenLastCalledWith(null);
  });

  it('rejects an already expired server receipt', async () => {
    upload.mockResolvedValue(receipt({ expires_at: new Date(Date.now() - 1000).toISOString() }));
    render(<ResearchInput onChange={vi.fn()} />);
    choose();
    expect(await screen.findByText(/This attachment has expired/)).toBeVisible();
  });

  it('shows a safe parser failure and allows selecting another file', async () => {
    upload.mockRejectedValueOnce(
      new ApiError(422, 'invalid_request', 'Document extraction failed.'),
    );
    upload.mockResolvedValueOnce(receipt());
    render(<ResearchInput onChange={vi.fn()} />);
    choose();
    expect(await screen.findByRole('alert')).toHaveTextContent('Document extraction failed.');
    choose();
    expect(await screen.findByText('Attached: notes.txt')).toBeVisible();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it.each(['empty', 'oversized', 'unsupported'])(
    'refuses %s files before sending bytes',
    (kind) => {
      const file =
        kind === 'empty'
          ? new File([], 'empty.txt')
          : new File(['x'], kind === 'unsupported' ? 'macro.exe' : 'huge.txt');
      if (kind === 'oversized')
        Object.defineProperty(file, 'size', { value: MAX_IMPORT_BYTES + 1 });
      render(<ResearchInput onChange={vi.fn()} />);
      choose(file);
      expect(screen.getByRole('alert')).toBeVisible();
      expect(upload).not.toHaveBeenCalled();
    },
  );

  it('aborts on unmount and respects disabled form state', async () => {
    upload.mockImplementation(() => new Promise(() => undefined));
    const changed = vi.fn();
    const view = render(<ResearchInput onChange={changed} disabled />);
    expect(screen.getByLabelText('Document or media')).toBeDisabled();
    view.rerender(<ResearchInput onChange={changed} />);
    choose();
    await waitFor(() => expect(upload).toHaveBeenCalledTimes(1));
    view.unmount();
    expect(upload.mock.calls[0]?.[1].aborted).toBe(true);
  });
});
