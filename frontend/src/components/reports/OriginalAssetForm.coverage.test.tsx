import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import * as api from '@/lib/api/originalAssets';
import type { EvidenceItem } from '@/lib/api/reports';
import { report } from '@/test/fixtures.reports';
import { OriginalAssetForm, eligibleOriginals } from './OriginalAssetForm';

const evidence: EvidenceItem = {
  ...report.version.evidence[0]!,
  label: 'E1',
  source_id: 'research_import',
  attributes: [
    { key: 'original_sha256', value: 'a'.repeat(64) },
    { key: 'filename', value: 'source.pdf' },
    { key: 'media_type', value: 'application/pdf' },
  ],
};
const asset: api.OriginalAsset = {
  id: 'asset-1',
  report_id: 'report-1',
  report_version_id: 'version-1',
  version_number: 1,
  evidence_label: 'E1',
  source_id: 'research_import',
  event_id: 'event-1',
  sha256: 'a'.repeat(64),
  byte_count: 3,
  filename: 'source.pdf',
  media_type: 'application/pdf',
  permitted_use: 'Allowed',
  owner_id: 'user-1',
  team_id: null,
  uploader_id: 'user-1',
  created_at: '2026-09-01T00:00:00Z',
  expires_at: '2026-10-01T00:00:00Z',
  reservation_expires_at: '2026-09-01T00:02:00Z',
  status: 'active',
  transitioned_at: null,
};
beforeEach(() => {
  vi.spyOn(api, 'reserveOriginalAsset').mockResolvedValue({ ...asset, status: 'reserved' });
  vi.spyOn(api, 'uploadOriginalAsset').mockResolvedValue(asset);
  vi.spyOn(api, 'deleteOriginalAsset').mockResolvedValue(undefined);
});
function mount(items = [evidence]) {
  const onSaved = vi.fn();
  return {
    ...render(
      <OriginalAssetForm reportId="report-1" version={1} evidence={items} onSaved={onSaved} />,
    ),
    onSaved,
  };
}
async function fill(file = new File(['abc'], 'uploaded.pdf')) {
  const user = userEvent.setup();
  await user.upload(screen.getByLabelText('Original file'), file);
  await user.type(screen.getByLabelText('Permitted-use declaration'), 'Allowed');
  return user;
}

it.each([0, 8 * 1024 * 1024 + 1])(
  'rejects invalid file byte count %s before reserving storage',
  async (size) => {
    mount();
    const file = new File(['abc'], 'source.pdf');
    Object.defineProperty(file, 'size', { value: size });
    const user = await fill(file);
    await user.click(screen.getByRole('button', { name: 'Retain original' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'non-empty original file no larger than 8 MiB',
    );
    expect(api.reserveOriginalAsset).not.toHaveBeenCalled();
  },
);

it('keeps submission disabled after clearing the file and requires a use declaration', async () => {
  mount();
  const user = userEvent.setup();
  await user.upload(screen.getByLabelText('Original file'), new File(['abc'], 'file.pdf'));
  expect(screen.getByRole('button', { name: 'Retain original' })).toBeDisabled();
  await user.type(screen.getByLabelText('Permitted-use declaration'), 'Allowed');
  await user.upload(screen.getByLabelText('Original file'), []);
  expect(screen.getByRole('button', { name: 'Retain original' })).toBeDisabled();
  fireEvent.submit(screen.getByRole('button', { name: 'Retain original' }).closest('form')!);
  expect(api.reserveOriginalAsset).not.toHaveBeenCalled();
});

it('uses the selected frozen original metadata and explicit retention period', async () => {
  vi.mocked(api.uploadOriginalAsset).mockResolvedValue({
    ...asset,
    evidence_label: 'E2',
    filename: 'second.pdf',
  });
  const second = {
    ...evidence,
    label: 'E2',
    attributes: evidence.attributes!.map((row) =>
      row.key === 'filename' ? { ...row, value: 'second.pdf' } : row,
    ),
  };
  mount([evidence, second]);
  const user = await fill();
  await user.selectOptions(screen.getByLabelText('Imported evidence'), 'E2');
  await user.clear(screen.getByLabelText('Retention days'));
  await user.type(screen.getByLabelText('Retention days'), '7');
  await user.click(screen.getByRole('button', { name: 'Retain original' }));
  await screen.findByText(/File retained/);
  expect(api.reserveOriginalAsset).toHaveBeenCalledWith(
    'report-1',
    expect.objectContaining({ evidence_label: 'E2', filename: 'second.pdf', retention_days: 7 }),
    expect.any(AbortSignal),
  );
});

it('does not submit an original whose evidence disappeared while the form was open', async () => {
  const view = mount();
  const user = await fill();
  view.rerender(
    <OriginalAssetForm
      reportId="report-1"
      version={1}
      evidence={[{ ...evidence, label: 'E2' }]}
      onSaved={view.onSaved}
    />,
  );
  await user.click(screen.getByRole('button', { name: 'Retain original' }));
  expect(api.reserveOriginalAsset).not.toHaveBeenCalled();
});

it('refuses non-active upload results and cleans the reservation without hiding the original failure', async () => {
  vi.mocked(api.uploadOriginalAsset).mockResolvedValue({ ...asset, status: 'uploading' });
  vi.mocked(api.deleteOriginalAsset).mockRejectedValue(new Error('Cleanup unavailable'));
  const { onSaved } = mount();
  const user = await fill();
  await user.click(screen.getByRole('button', { name: 'Retain original' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('The original was not retained');
  await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
  expect(api.deleteOriginalAsset).toHaveBeenCalledOnce();
  expect(screen.getByLabelText<HTMLInputElement>('Original file').files).toHaveLength(0);
});

it('cancels before reservation completes without uploading a late reservation', async () => {
  let finish!: (value: api.OriginalAsset) => void;
  const pending = new Promise<api.OriginalAsset>((done) => {
    finish = done;
  });
  vi.mocked(api.reserveOriginalAsset).mockReturnValue(pending);
  const { onSaved } = mount();
  const user = await fill();
  await user.click(screen.getByRole('button', { name: 'Retain original' }));
  await user.click(screen.getByRole('button', { name: 'Cancel upload' }));
  await screen.findByText('Upload cancelled.');
  await act(async () => {
    finish({ ...asset, status: 'reserved' });
    await pending;
  });
  expect(api.uploadOriginalAsset).not.toHaveBeenCalled();
  expect(api.deleteOriginalAsset).not.toHaveBeenCalled();
  expect(onSaved).toHaveBeenCalledOnce();
});

it('reports failed cancellation and suppresses late upload success', async () => {
  let finish!: (value: api.OriginalAsset) => void;
  const pending = new Promise<api.OriginalAsset>((done) => {
    finish = done;
  });
  vi.mocked(api.uploadOriginalAsset).mockReturnValue(pending);
  vi.mocked(api.deleteOriginalAsset).mockRejectedValue(new Error('Cannot release reservation'));
  const { onSaved } = mount();
  const user = await fill();
  await user.click(screen.getByRole('button', { name: 'Retain original' }));
  await waitFor(() => expect(api.uploadOriginalAsset).toHaveBeenCalledOnce());
  await user.click(screen.getByRole('button', { name: 'Cancel upload' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Cannot release reservation');
  await act(async () => {
    finish(asset);
    await pending;
  });
  expect(onSaved).not.toHaveBeenCalled();
  expect(screen.queryByText(/File retained/)).not.toBeInTheDocument();
});

it('ignores cancellation failure after the form unmounts', async () => {
  vi.mocked(api.uploadOriginalAsset).mockReturnValue(new Promise(() => undefined));
  let reject!: (error: Error) => void;
  const pending = new Promise<void>((_done, fail) => {
    reject = fail;
  });
  vi.mocked(api.deleteOriginalAsset).mockReturnValue(pending);
  const { onSaved, unmount } = mount();
  const user = await fill();
  await user.click(screen.getByRole('button', { name: 'Retain original' }));
  await waitFor(() => expect(api.uploadOriginalAsset).toHaveBeenCalledOnce());
  await user.click(screen.getByRole('button', { name: 'Cancel upload' }));
  unmount();
  await act(async () => {
    reject(new Error('Late cancellation failure'));
    await pending.catch(() => undefined);
  });
  expect(onSaved).not.toHaveBeenCalled();
});

it('shows an empty state for originals without complete frozen metadata', () => {
  expect(eligibleOriginals([{ ...evidence, attributes: undefined }])).toEqual([]);
  mount([
    { ...evidence, attributes: evidence.attributes!.filter((row) => row.key !== 'media_type') },
  ]);
  expect(screen.getByText(/no eligible imported original-file hash/)).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Retain original' })).not.toBeInTheDocument();
});
