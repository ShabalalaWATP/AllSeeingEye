import { act, render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';

import { fetchEvidencePackage } from '@/lib/api/reportDocuments';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { applySession } from '@/test/render';
import { EvidencePackageDownload } from './EvidencePackageDownload';

vi.mock('@/lib/api/reportDocuments', () => ({ fetchEvidencePackage: vi.fn() }));
vi.mock('@/lib/downloadBinary', () => ({ saveBinaryFile: vi.fn() }));
beforeEach(() => {
  vi.clearAllMocks();
  applySession('user');
});

it('downloads exactly the selected version with captured-file limitations', async () => {
  const blob = new Blob(['fixture zip']);
  vi.mocked(fetchEvidencePackage).mockResolvedValue(blob);
  render(<EvidencePackageDownload id="report" version={3} title="Review" />);
  await userEvent.click(screen.getByRole('button', { name: 'Download evidence package' }));
  await waitFor(() =>
    expect(saveBinaryFile).toHaveBeenCalledWith(expect.stringContaining('v3'), blob),
  );
  expect(fetchEvidencePackage).toHaveBeenCalledWith('report', 3, expect.any(AbortSignal));
  expect(screen.getByText(/Original source files are not included/)).toBeInTheDocument();
});

it.each(['access', 'account', 'unmount'])(
  'aborts on %s change and discards late private bytes',
  async (change) => {
    let resolve!: (value: Blob) => void;
    vi.mocked(fetchEvidencePackage).mockImplementation(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    );
    const rendered = render(<EvidencePackageDownload id="report" version={2} title="Review" />);
    await userEvent.click(screen.getByRole('button', { name: 'Download evidence package' }));
    const signal = vi.mocked(fetchEvidencePackage).mock.calls[0]![2];
    act(() => {
      if (change === 'access') invalidateWorkspaceAccess();
      else if (change === 'account') applySession('admin');
      else rendered.unmount();
    });
    expect(signal.aborted).toBe(true);
    await act(async () => {
      resolve(new Blob(['late private bytes']));
      await Promise.resolve();
    });
    expect(saveBinaryFile).not.toHaveBeenCalled();
  },
);
