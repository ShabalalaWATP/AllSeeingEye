import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import type { ResearchInputReceipt } from '@/lib/api/researchInputs';
import { SecAttachmentSummary } from './SecAttachmentSummary';
const receipt: ResearchInputReceipt = {
  id: '10000000-0000-4000-8000-000000000001',
  filename: 'filing.htm',
  media_type: 'text/html',
  sha256: 'a'.repeat(64),
  imported_at: '2026-09-08T00:00:00Z',
  expires_at: '2026-09-08T00:15:00Z',
  event_count: 2,
  extracted_characters: 200,
  preview: '<script>untrusted filing text</script>',
  limitations: ['Filed statements are not independently verified.'],
  previews: [],
};
it('distinguishes imported document text from metadata and never renders filing markup as HTML', async () => {
  const download = vi.fn();
  const remove = vi.fn();
  const { container } = render(
    <SecAttachmentSummary
      receipt={receipt}
      originalExpiresAt={receipt.expires_at}
      disabled={false}
      downloading={false}
      onDownload={download}
      onRemove={remove}
    />,
  );
  expect(
    screen.getByText(/Research uses this imported document, not just the filing listing/),
  ).toBeInTheDocument();
  expect(screen.getByText(/does not preserve the original permanently/)).toBeInTheDocument();
  await userEvent.click(screen.getByText('Extracted document preview and limitations'));
  expect(screen.getByText('<script>untrusted filing text</script>')).toBeVisible();
  expect(container.querySelector('script')).toBeNull();
  await userEvent.click(
    screen.getByRole('button', { name: 'Download temporary original document' }),
  );
  expect(download).toHaveBeenCalledOnce();
  await userEvent.click(screen.getByRole('button', { name: 'Remove filing attachment' }));
  expect(remove).toHaveBeenCalledOnce();
});
it('honours busy/disabled state and identifies absent extracted preview', () => {
  render(
    <SecAttachmentSummary
      receipt={{ ...receipt, preview: '' }}
      originalExpiresAt={receipt.expires_at}
      disabled
      downloading
      onDownload={vi.fn()}
      onRemove={vi.fn()}
    />,
  );
  expect(
    screen.getByRole('button', { name: 'Download temporary original document' }),
  ).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Remove filing attachment' })).toBeDisabled();
  expect(screen.getByText('No text preview available.')).toBeInTheDocument();
});
