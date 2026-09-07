import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { server } from '@/test/server';
import { plainUser, adminUser } from '@/test/fixtures';
import { useAuthStore } from '@/stores/auth';
import { saveBinaryFile } from '@/lib/downloadBinary';
import type { OriginalAsset } from '@/lib/api/originalAssets';
import type { EvidenceItem } from '@/lib/api/reports';
import { OriginalAssets } from './OriginalAssets';
import { eligibleOriginals } from './OriginalAssetForm';
import { ClaimExportSelection } from './ClaimExportSelection';

vi.mock('@/lib/downloadBinary', () => ({ saveBinaryFile: vi.fn() }));
const asset: OriginalAsset = {
  id: 'asset-1',
  report_id: 'report-1',
  report_version_id: 'version-1',
  version_number: 1,
  evidence_label: 'E1',
  source_id: 'research_import',
  event_id: 'event-1',
  sha256: 'a'.repeat(64),
  byte_count: 3,
  filename: 'original.pdf',
  media_type: 'application/pdf',
  permitted_use: 'Public licence',
  owner_id: 'user-1',
  team_id: null,
  uploader_id: 'user-1',
  created_at: '2026-09-07T00:00:00Z',
  expires_at: '2099-01-01T00:00:00Z',
  reservation_expires_at: '2099-01-01T00:00:00Z',
  status: 'active',
  transitioned_at: null,
};
const evidence = {
  label: 'E1',
  source_id: 'research_import',
  title: 'Imported document',
  attributes: [
    { key: 'original_sha256', value: 'a'.repeat(64) },
    { key: 'filename', value: 'original.pdf' },
    { key: 'media_type', value: 'application/pdf' },
  ],
} as EvidenceItem;
function panel(version = 1, canEdit = true) {
  return (
    <ClaimExportSelection reportId="report-1" version={version}>
      <OriginalAssets
        reportId="report-1"
        version={version}
        evidence={[evidence]}
        canEdit={canEdit}
      />
    </ClaimExportSelection>
  );
}
function list(items: OriginalAsset[] = [asset]) {
  server.use(http.get('/api/reports/report-1/original-assets', () => HttpResponse.json({ items })));
}
it('exports selected original IDs and removes selection when bytes are deleted', async () => {
  list();
  let payload: unknown;
  server.use(
    http.post('/api/reports/report-1/selected-evidence-package', async ({ request }) => {
      payload = await request.json();
      return new HttpResponse('zip');
    }),
    http.delete('/api/reports/report-1/original-assets/asset-1', () => {
      list([]);
      return new HttpResponse(null, { status: 204 });
    }),
  );
  render(panel());
  const user = userEvent.setup();
  await user.click(
    await screen.findByLabelText('Include original original.pdf in evidence package'),
  );
  await user.click(screen.getByRole('button', { name: 'Download selected evidence' }));
  await waitFor(() =>
    expect(payload).toEqual({ version_number: 1, revisions: [], asset_ids: ['asset-1'] }),
  );
  await user.click(screen.getByRole('button', { name: 'Delete retained original' }));
  await user.click(screen.getByRole('button', { name: 'Confirm deletion' }));
  await screen.findByText('No originals retained for this version.');
  expect(screen.getByText('0 of 20 revisions selected')).toBeInTheDocument();
});
it('downloads inert bytes with a generated name and hides write controls for readers', async () => {
  vi.mocked(saveBinaryFile).mockClear();
  list();
  server.use(
    http.get(
      '/api/reports/report-1/original-assets/asset-1/content',
      () => new HttpResponse('abc'),
    ),
  );
  render(panel(1, false));
  await userEvent.click(await screen.findByRole('button', { name: 'Download original' }));
  await waitFor(() =>
    expect(saveBinaryFile).toHaveBeenCalledWith(
      'original-asset-1.bin',
      expect.objectContaining({ size: 3 }),
    ),
  );
  expect(screen.queryByRole('button', { name: 'Retain original' })).not.toBeInTheDocument();
  expect(
    screen.queryByRole('button', { name: 'Delete retained original' }),
  ).not.toBeInTheDocument();
});
it.each([false, true])('reserves then submits original bytes; mismatch=%s', async (mismatch) => {
  list([]);
  let reservation: unknown;
  let uploaded = false;
  let deleted = false;
  server.use(
    http.post('/api/reports/report-1/original-assets', async ({ request }) => {
      reservation = await request.json();
      return HttpResponse.json({ ...asset, status: 'reserved' });
    }),
    http.put('/api/reports/report-1/original-assets/asset-1/content', ({ request }) => {
      uploaded = request.headers.get('Content-Type') === 'application/octet-stream';
      return mismatch
        ? HttpResponse.json(
            { error: { code: 'hash_mismatch', message: 'Original bytes do not match.' } },
            { status: 422 },
          )
        : HttpResponse.json(asset);
    }),
    http.delete('/api/reports/report-1/original-assets/asset-1', () => {
      deleted = true;
      return new HttpResponse(null, { status: 204 });
    }),
  );
  render(panel());
  const user = userEvent.setup();
  await user.upload(screen.getByLabelText('Original file'), new File(['abc'], 'renamed.unknown'));
  await user.type(screen.getByLabelText('Permitted-use declaration'), 'Public licence');
  await user.click(screen.getByRole('button', { name: 'Retain original' }));
  if (mismatch) {
    await screen.findByText('Original bytes do not match.');
    await waitFor(() => expect(deleted).toBe(true));
  } else
    await screen.findByText('Original bytes matched the frozen SHA-256 for E1. File retained.');
  expect(uploaded).toBe(true);
  expect(reservation).toEqual({
    version_number: 1,
    evidence_label: 'E1',
    filename: 'original.pdf',
    media_type: 'application/pdf',
    byte_count: 3,
    permitted_use: 'Public licence',
    retention_days: 30,
  });
  expect(screen.getByLabelText<HTMLInputElement>('Original file').files).toHaveLength(0);
});
it('clears private draft and selections on account and version changes', async () => {
  list();
  useAuthStore.setState({ status: 'authenticated', user: plainUser });
  const view = render(panel());
  await userEvent.type(screen.getByLabelText('Permitted-use declaration'), 'Private note');
  await userEvent.click(
    await screen.findByLabelText('Include original original.pdf in evidence package'),
  );
  act(() => useAuthStore.setState({ user: adminUser }));
  expect(screen.getByLabelText('Permitted-use declaration')).toHaveValue('');
  expect(screen.getByText('0 of 20 revisions selected')).toBeInTheDocument();
  await userEvent.type(screen.getByLabelText('Permitted-use declaration'), 'Another note');
  view.rerender(panel(2));
  expect(screen.getByLabelText('Permitted-use declaration')).toHaveValue('');
});
it('rejects duplicate attributes and content or thumbnail hashes as original anchors', () => {
  expect(eligibleOriginals([evidence])).toHaveLength(1);
  expect(eligibleOriginals([evidence, evidence])).toHaveLength(0);
  expect(
    eligibleOriginals([
      { ...evidence, attributes: [...evidence.attributes!, ...evidence.attributes!] },
    ]),
  ).toHaveLength(0);
  expect(
    eligibleOriginals([
      {
        ...evidence,
        attributes: [{ key: 'sample_sha256', value: 'a'.repeat(64) }],
        content_hash: 'a'.repeat(64),
      },
    ]),
  ).toHaveLength(0);
});

it('cancels an in-flight upload and releases its reservation', async () => {
  list([]);
  let started = false;
  let deleted = false;
  let finish: (() => void) | undefined;
  server.use(
    http.post('/api/reports/report-1/original-assets', () =>
      HttpResponse.json({ ...asset, status: 'reserved' }),
    ),
    http.put('/api/reports/report-1/original-assets/asset-1/content', async () => {
      started = true;
      await new Promise<void>((resolve) => {
        finish = resolve;
      });
      return HttpResponse.json(asset);
    }),
    http.delete('/api/reports/report-1/original-assets/asset-1', () => {
      deleted = true;
      return new HttpResponse(null, { status: 204 });
    }),
  );
  render(panel());
  const user = userEvent.setup();
  await user.upload(screen.getByLabelText('Original file'), new File(['abc'], 'file.pdf'));
  await user.type(screen.getByLabelText('Permitted-use declaration'), 'Public licence');
  await user.click(screen.getByRole('button', { name: 'Retain original' }));
  await waitFor(() => expect(started).toBe(true));
  await user.click(screen.getByRole('button', { name: 'Cancel upload' }));
  await screen.findByText('Upload cancelled.');
  expect(deleted).toBe(true);
  act(() => {
    finish?.();
  });
  expect(screen.queryByText(/File retained/)).not.toBeInTheDocument();
});
