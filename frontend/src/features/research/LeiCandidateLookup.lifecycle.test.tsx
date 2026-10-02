import { act, render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';

import { findLeiCandidates } from '@/lib/api/leiCandidates';
import { LeiCandidateLookup } from './LeiCandidateLookup';

vi.mock('@/lib/api/leiCandidates', () => ({ findLeiCandidates: vi.fn() }));

type Result = Awaited<ReturnType<typeof findLeiCandidates>>;
const candidate = {
  lei: '5493001KJTIIGC8Y1R12',
  name: 'Current company',
  jurisdiction: 'GB',
  status: 'ACTIVE',
};

function pending() {
  let resolve!: (result: Result) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<Result>((success, failure) => {
    resolve = success;
    reject = failure;
  });
  return { promise, resolve, reject };
}

beforeEach(() => vi.mocked(findLeiCandidates).mockReset());

it('shows a failed lookup, then clears that error when an explicit retry returns no candidates', async () => {
  vi.mocked(findLeiCandidates)
    .mockRejectedValueOnce(new Error('Provider unavailable'))
    .mockResolvedValueOnce({ items: [] });
  const confirm = vi.fn();
  render(<LeiCandidateLookup initialName="Example" disabled={false} confirm={confirm} />);
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Search GLEIF' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('GLEIF lookup failed');
  expect(screen.getByRole('button', { name: 'Search GLEIF' })).toBeEnabled();
  await user.click(screen.getByRole('button', { name: 'Search GLEIF' }));
  expect(await screen.findByRole('status')).toHaveTextContent('No candidates returned');
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(confirm).not.toHaveBeenCalled();
});

it('discards a cancelled result without clearing the busy state of the replacement lookup', async () => {
  const old = pending();
  const current = pending();
  vi.mocked(findLeiCandidates)
    .mockReturnValueOnce(old.promise)
    .mockReturnValueOnce(current.promise);
  const confirm = vi.fn();
  render(<LeiCandidateLookup initialName="Original company" disabled={false} confirm={confirm} />);
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Search GLEIF' }));
  const oldSignal = vi.mocked(findLeiCandidates).mock.calls[0]![2];
  await user.clear(screen.getByLabelText('Company name for GLEIF'));
  await user.type(screen.getByLabelText('Company name for GLEIF'), 'Current company');
  expect(oldSignal.aborted).toBe(true);
  await user.click(screen.getByRole('button', { name: 'Search GLEIF' }));
  await act(async () => {
    old.resolve({ items: [{ ...candidate, name: 'Stale company' }] });
    await old.promise;
  });
  expect(screen.getByRole('button', { name: 'Searching GLEIF…' })).toBeDisabled();
  expect(screen.queryByText(/Stale company/)).not.toBeInTheDocument();
  await act(async () => {
    current.resolve({ items: [candidate] });
    await current.promise;
  });
  await user.click(screen.getByRole('button', { name: /Confirm Current company/ }));
  expect(confirm).toHaveBeenCalledExactlyOnceWith(candidate.lei);
});

it('suppresses a cancelled failure when the country changes and validates the new country', async () => {
  const request = pending();
  vi.mocked(findLeiCandidates).mockReturnValueOnce(request.promise);
  const confirm = vi.fn();
  render(<LeiCandidateLookup initialName="Example" disabled={false} confirm={confirm} />);
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Search GLEIF' }));
  const signal = vi.mocked(findLeiCandidates).mock.calls[0]![2];
  const country = screen.getByLabelText('GLEIF country code (optional)');
  await user.type(country, 'g');
  expect(signal.aborted).toBe(true);
  expect(screen.getByRole('button', { name: 'Search GLEIF' })).toBeDisabled();
  await act(async () => {
    request.reject(new Error('Cancelled lookup failed'));
    await Promise.resolve();
  });
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  await user.type(country, 'b');
  expect(country).toHaveValue('GB');
  expect(screen.getByRole('button', { name: 'Search GLEIF' })).toBeEnabled();
  expect(confirm).not.toHaveBeenCalled();
  expect(findLeiCandidates).toHaveBeenCalledTimes(1);
});
