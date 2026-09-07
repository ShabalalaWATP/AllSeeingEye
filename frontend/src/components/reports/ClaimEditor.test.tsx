import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { report } from '@/test/fixtures';
import { ApiError } from '@/lib/api/errors';
import type { ClaimRevision } from '@/lib/api/claims';
import { createClaim, updateClaim } from '@/lib/api/claims';
import { ClaimEditor } from './ClaimEditor';
import { ClaimCitationPicker } from './ClaimCitationPicker';
import { selectedExcerpt } from './claimExcerpt';

vi.mock('@/lib/api/claims', () => ({
  createClaim: vi.fn().mockResolvedValue({}),
  updateClaim: vi.fn(),
}));

it('uses code-point offsets and rejects split surrogate pairs', () => {
  expect(selectedExcerpt('🛰中国项目', 2, 6)).toEqual({ start: 1, end: 5, text: '中国项目' });
  expect(selectedExcerpt('🛰中国项目', 1, 3)).toBeNull();
  expect(selectedExcerpt('text', 2, 2)).toBeNull();
  expect(selectedExcerpt('x'.repeat(1201), 0, 1201)).toBeNull();
});

it('submits a proposed claim with selected original text and a revision reason', async () => {
  const evidence = report.version.evidence.map((row) => ({ ...row, title: '🛰中国项目' }));
  const saved = vi.fn();
  render(
    <ClaimEditor
      reportId="report-1"
      version={3}
      evidence={evidence}
      onSaved={saved}
      onCancel={vi.fn()}
    />,
  );
  const user = userEvent.setup();
  expect(screen.getByRole('button', { name: 'Save proposed claim' })).toBeDisabled();
  await user.type(screen.getByLabelText('Claim statement'), 'The source names a Chinese project.');
  await user.type(screen.getByLabelText('Reason for this revision'), 'Record attribution.');
  const text = screen.getByLabelText<HTMLTextAreaElement>('Select the exact excerpt');
  text.setSelectionRange(2, 6);
  fireEvent.select(text);
  await user.click(screen.getByRole('button', { name: 'Add selected excerpt' }));
  await user.click(screen.getByRole('button', { name: 'Save proposed claim' }));
  await waitFor(() => expect(saved).toHaveBeenCalledOnce());
  expect(createClaim).toHaveBeenCalledWith(
    expect.objectContaining({
      report_id: 'report-1',
      version_number: 3,
      state: 'proposed',
      reason: 'Record attribution.',
      citations: [
        expect.objectContaining({ text: '中国项目', start: 1, end: 5, relation: 'supporting' }),
      ],
    }),
    expect.any(AbortSignal),
  );
});

const current: ClaimRevision = {
  id: 'revision-1',
  claim_id: 'claim-1',
  report_id: 'report-1',
  report_version_id: 'version-1',
  number: 1,
  previous_id: null,
  statement: 'Original assertion',
  kind: 'reported_fact',
  state: 'proposed',
  citations: [
    {
      label: 'E1',
      relation: 'supporting',
      event_id: 'event-1',
      source_content_hash: 'hash',
      excerpt: { field: 'title', start: 0, end: 4, text: 'Text', sha256: 'hash' },
    },
  ],
  unresolved_conflicts: ['Date remains unknown.'],
  reason: 'Initial capture',
  authored_by: 'user-1',
  created_at: '2026-09-07T00:00:00Z',
};

it('appends a withdrawal against the exact base revision and retains its evidence', async () => {
  vi.mocked(updateClaim).mockResolvedValueOnce({ ...current, id: 'revision-2', number: 2 });
  const saved = vi.fn();
  render(
    <ClaimEditor
      reportId="report-1"
      version={1}
      evidence={report.version.evidence}
      current={current}
      onSaved={saved}
      onCancel={vi.fn()}
    />,
  );
  const user = userEvent.setup();
  await user.selectOptions(screen.getByLabelText('Review state'), 'withdrawn');
  await user.type(screen.getByLabelText('Reason for this revision'), 'Attribution is unresolved.');
  await user.click(screen.getByRole('button', { name: 'Save new revision' }));
  await waitFor(() => expect(saved).toHaveBeenCalledOnce());
  expect(updateClaim).toHaveBeenLastCalledWith(
    'claim-1',
    expect.objectContaining({
      base_revision_id: 'revision-1',
      state: 'withdrawn',
      unresolved_conflicts: ['Date remains unknown.'],
      citations: [expect.objectContaining({ label: 'E1', text: 'Text' })],
    }),
    expect.any(AbortSignal),
  );
  expect(current.state).toBe('proposed');
});

it('keeps a stale edit visible and requires reloading rather than reporting success', async () => {
  vi.mocked(updateClaim).mockRejectedValueOnce(
    new ApiError(409, 'conflict', 'A newer revision exists.'),
  );
  const saved = vi.fn();
  render(
    <ClaimEditor
      reportId="report-1"
      version={1}
      evidence={report.version.evidence}
      current={current}
      onSaved={saved}
      onCancel={vi.fn()}
    />,
  );
  const user = userEvent.setup();
  await user.type(screen.getByLabelText('Reason for this revision'), 'Check attribution.');
  await user.click(screen.getByRole('button', { name: 'Save new revision' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('reload the latest claim');
  expect(saved).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Claim statement')).toHaveValue('Original assertion');
});

it.each(['\r\n', '\r'])(
  'maps textarea selections across original %j line endings',
  async (newline) => {
    const evidence = report.version.evidence.map((row) => ({
      ...row,
      title: `Before${newline}中国项目`,
    }));
    const add = vi.fn();
    render(<ClaimCitationPicker evidence={evidence} onAdd={add} />);
    const text = screen.getByLabelText<HTMLTextAreaElement>('Select the exact excerpt');
    expect(text.value).toBe('Before\n中国项目');
    text.setSelectionRange(7, 11);
    fireEvent.select(text);
    await userEvent.click(screen.getByRole('button', { name: 'Add selected excerpt' }));
    expect(add).toHaveBeenCalledWith(
      expect.objectContaining({
        text: '中国项目',
        start: 6 + newline.length,
        end: 10 + newline.length,
      }),
    );
  },
);

it('locks editing while saving and suppresses completion after unmount', async () => {
  let finish: (value: ClaimRevision) => void = () => undefined;
  vi.mocked(updateClaim).mockReturnValueOnce(
    new Promise((resolve) => {
      finish = resolve;
    }),
  );
  const saved = vi.fn();
  const page = render(
    <ClaimEditor
      reportId="report-1"
      version={1}
      evidence={report.version.evidence}
      current={current}
      onSaved={saved}
      onCancel={vi.fn()}
    />,
  );
  await userEvent.type(screen.getByLabelText('Reason for this revision'), 'Review attribution.');
  await userEvent.click(screen.getByRole('button', { name: 'Save new revision' }));
  expect(screen.getByLabelText('Claim statement')).toBeDisabled();
  expect(screen.getByLabelText('Review state')).toBeDisabled();
  const signal = vi.mocked(updateClaim).mock.calls.at(-1)?.[2];
  page.unmount();
  expect(signal?.aborted).toBe(true);
  await act(async () => {
    finish({ ...current, number: 2 });
    await Promise.resolve();
  });
  expect(saved).not.toHaveBeenCalled();
});
