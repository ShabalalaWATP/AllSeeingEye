import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { searchSecFilings, importSecFiling, downloadSecOriginal } from '@/lib/api/secFilings';
import { secPage, secChoice, secReceipt } from '@/test/fixtures.secFilings';
import { applySession } from '@/test/render';
import { SecFilingPicker } from './SecFilingPicker';
vi.mock('@/lib/api/secFilings', () => ({
  searchSecFilings: vi.fn(),
  importSecFiling: vi.fn(),
  downloadSecOriginal: vi.fn(),
}));
beforeEach(() => {
  vi.useFakeTimers();
  applySession('user');
  vi.mocked(searchSecFilings).mockResolvedValue(secPage());
  vi.mocked(importSecFiling).mockResolvedValue(secReceipt());
});
afterEach(() => vi.useRealTimers());
async function discover() {
  const changed = vi.fn();
  render(<SecFilingPicker onChange={changed} />);
  fireEvent.change(screen.getByLabelText('SEC company identifier (CIK)'), {
    target: { value: '320193' },
  });
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: 'Discover SEC filings' }));
    await Promise.resolve();
  });
  return changed;
}
it('clears the real attached research input when its retention timer expires', async () => {
  const changed = await discover();
  await act(async () => {
    fireEvent.click(
      screen.getByRole('button', { name: `Import document ${secChoice().accession}` }),
    );
    await Promise.resolve();
  });
  expect(changed).toHaveBeenLastCalledWith(secReceipt().id);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(15 * 60000 + 1);
  });
  expect(changed).toHaveBeenLastCalledWith(null);
  expect(screen.getByText(/This imported filing has expired/)).toBeInTheDocument();
  expect(
    screen.queryByRole('heading', { name: 'Attached filing document: filing.htm' }),
  ).not.toBeInTheDocument();
});
it('requires fresh discovery when an opaque selection has expired', async () => {
  vi.mocked(searchSecFilings).mockResolvedValue(
    secPage({ items: [secChoice({ expires_at: new Date(Date.now() + 1000).toISOString() })] }),
  );
  await discover();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1001);
  });
  fireEvent.click(screen.getByRole('button', { name: `Import document ${secChoice().accession}` }));
  expect(
    screen.getByText('This filing selection has expired. Run discovery again.'),
  ).toBeInTheDocument();
  expect(importSecFiling).not.toHaveBeenCalled();
});
it('does not fetch an expired original while preserving a still-valid extracted input', async () => {
  vi.mocked(searchSecFilings).mockResolvedValue(
    secPage({ items: [secChoice({ expires_at: new Date(Date.now() + 1000).toISOString() })] }),
  );
  const changed = await discover();
  await act(async () => {
    fireEvent.click(
      screen.getByRole('button', { name: `Import document ${secChoice().accession}` }),
    );
    await Promise.resolve();
  });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1001);
  });
  fireEvent.click(screen.getByRole('button', { name: 'Download temporary original document' }));
  expect(screen.getByText(/The temporary original has expired/)).toBeInTheDocument();
  expect(downloadSecOriginal).not.toHaveBeenCalled();
  expect(changed).toHaveBeenLastCalledWith(secReceipt().id);
});
