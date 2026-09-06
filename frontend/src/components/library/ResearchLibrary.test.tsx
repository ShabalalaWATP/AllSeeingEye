import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { beforeEach, expect, it, vi } from 'vitest';
import { fetchLibrary } from '@/lib/api/researchLibrary';
import { reportSummary } from '@/test/fixtures.reports';
import { applySession } from '@/test/render';
import { ResearchLibrary } from './ResearchLibrary';
vi.mock('@/lib/api/researchLibrary', () => ({ fetchLibrary: vi.fn() }));
vi.mock('./LibraryButton', () => ({ LibraryButton: () => <span>Organise report</span> }));
beforeEach(() => {
  vi.clearAllMocks();
  applySession('user');
});
it('renders private annotations and applies filters and pagination', async () => {
  const preference = {
    favourite: true,
    tags: ['review'],
    note: 'Private annotation',
    updated_at: '2026-09-01',
  };
  vi.mocked(fetchLibrary).mockResolvedValue({
    items: [
      { report: reportSummary, preference },
      {
        report: { ...reportSummary, id: 'second', team_id: 'team' },
        preference: { ...preference, favourite: false, tags: [], note: null },
      },
    ],
    total: 21,
    offset: 0,
    limit: 20,
  });
  render(
    <MemoryRouter>
      <ResearchLibrary revision={0} onChanged={vi.fn()} />
    </MemoryRouter>,
  );
  await screen.findByText('Private annotation');
  expect(screen.getByText('Tags: review')).toBeInTheDocument();
  fireEvent.click(screen.getByText('Next saved reports'));
  await waitFor(() => expect(fetchLibrary).toHaveBeenLastCalledWith(20, false, ''));
  fireEvent.click(await screen.findByText('Previous saved reports'));
  await waitFor(() => expect(fetchLibrary).toHaveBeenLastCalledWith(0, false, ''));
  fireEvent.click(screen.getByLabelText('Favourites only'));
  await waitFor(() => expect(fetchLibrary).toHaveBeenLastCalledWith(0, true, ''));
  fireEvent.change(screen.getByLabelText('Filter by exact tag'), { target: { value: 'review' } });
  fireEvent.click(screen.getByText('Apply tag filter'));
  await waitFor(() => expect(fetchLibrary).toHaveBeenLastCalledWith(0, true, 'review'));
});
it('retries library failures and explains empty results', async () => {
  vi.mocked(fetchLibrary)
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValue({ items: [], total: 0, offset: 0, limit: 20 });
  render(
    <MemoryRouter>
      <ResearchLibrary revision={0} onChanged={vi.fn()} />
    </MemoryRouter>,
  );
  fireEvent.click(await screen.findByText('Retry library'));
  expect(await screen.findByText(/No saved reports on this page/)).toBeInTheDocument();
});
