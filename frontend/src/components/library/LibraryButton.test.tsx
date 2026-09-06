import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import {
  fetchLibraryPreference,
  saveLibraryPreference,
  removeLibraryPreference,
} from '@/lib/api/researchLibrary';
import { applySession } from '@/test/render';
import { LibraryButton } from './LibraryButton';
vi.mock('@/lib/api/researchLibrary', () => ({
  fetchLibraryPreference: vi.fn(),
  saveLibraryPreference: vi.fn(),
  removeLibraryPreference: vi.fn(),
}));
const preference = { favourite: false, tags: [], note: null, updated_at: null };
beforeEach(() => {
  vi.clearAllMocks();
  applySession('user');
  vi.mocked(fetchLibraryPreference).mockResolvedValue(preference);
  vi.mocked(saveLibraryPreference).mockResolvedValue(preference);
});
async function open() {
  const changed = vi.fn();
  const view = render(<LibraryButton reportId="report" onChanged={changed} />);
  fireEvent.click(screen.getByText('Save / organise'));
  await screen.findByLabelText('Private note');
  return { ...view, changed };
}
it('saves personal tags, favourite and note then closes', async () => {
  const view = await open();
  fireEvent.click(screen.getByLabelText('Favourite'));
  fireEvent.change(screen.getByLabelText('Tags, separated by commas'), {
    target: { value: 'Iran, , review' },
  });
  fireEvent.change(screen.getByLabelText('Private note'), { target: { value: 'Check original' } });
  fireEvent.submit(screen.getByRole('form'));
  await waitFor(() => expect(view.changed).toHaveBeenCalled());
  expect(saveLibraryPreference).toHaveBeenCalledWith(
    'report',
    { favourite: true, tags: ['Iran', 'review'], note: 'Check original' },
    expect.any(AbortSignal),
  );
  expect(screen.queryByLabelText('Private note')).not.toBeInTheDocument();
});
it('requires explicit removal and leaves report intact', async () => {
  vi.mocked(fetchLibraryPreference).mockResolvedValue({
    ...preference,
    updated_at: '2026-09-01',
    note: 'Saved',
  });
  const view = await open();
  fireEvent.click(screen.getByText('Remove from my library'));
  expect(removeLibraryPreference).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText('Confirm removal'));
  await waitFor(() => expect(view.changed).toHaveBeenCalled());
  expect(removeLibraryPreference).toHaveBeenCalledWith('report', expect.any(AbortSignal));
});
it('retries failed preference loading', async () => {
  vi.mocked(fetchLibraryPreference).mockRejectedValueOnce(new Error('offline'));
  render(<LibraryButton reportId="report" onChanged={vi.fn()} />);
  fireEvent.click(screen.getByText('Save / organise'));
  fireEvent.click(await screen.findByText('Retry library settings'));
  await screen.findByLabelText('Private note');
  fireEvent.click(screen.getByText('Close library settings'));
  expect(screen.queryByLabelText('Private note')).not.toBeInTheDocument();
});
it('retains edits on save failure and sends blank note as null', async () => {
  vi.mocked(saveLibraryPreference).mockRejectedValueOnce(new Error('offline'));
  await open();
  fireEvent.submit(screen.getByRole('form'));
  await screen.findByRole('alert');
  expect(saveLibraryPreference).toHaveBeenCalledWith(
    'report',
    { favourite: false, tags: [], note: null },
    expect.any(AbortSignal),
  );
  expect(screen.getByLabelText('Private note')).toBeInTheDocument();
});
it('aborts a pending save on account change', async () => {
  let resolve!: (value: typeof preference) => void;
  vi.mocked(saveLibraryPreference).mockImplementation(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  const view = await open();
  fireEvent.submit(screen.getByRole('form'));
  const signal = vi.mocked(saveLibraryPreference).mock.calls[0]![2];
  act(() => applySession('admin'));
  expect(signal.aborted).toBe(true);
  await act(async () => {
    resolve(preference);
    await Promise.resolve();
  });
  expect(view.changed).not.toHaveBeenCalled();
});
