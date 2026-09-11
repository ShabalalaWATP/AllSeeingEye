import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { applySession } from '@/test/render';
import { reportJob, jobId } from '@/test/reportJobFixture';
import { server } from '@/test/server';
import { useAuthStore } from '@/stores/auth';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import ReportJobPage from './ReportJobPage';

function mount() {
  applySession('user');
  render(
    <MemoryRouter initialEntries={[`/research/jobs/${jobId}`]}>
      <Routes>
        <Route path="/research/jobs/:id" element={<ReportJobPage />} />
        <Route path="/research/jobs" element={<h1>Job list destination</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

it.each(['paused', 'failed'] as const)(
  'confirms a %s discard before deleting and returns to the job list',
  async (status) => {
    const discard = vi.fn(() => new HttpResponse(null, { status: 204 }));
    server.use(
      http.get('/api/report-jobs/:id', () => HttpResponse.json(reportJob({ status }))),
      http.delete('/api/report-jobs/:id', discard),
    );
    mount();
    fireEvent.click(await screen.findByRole('button', { name: 'Discard job' }));
    expect(
      screen.getByText(
        'Discard this unfinished research job? Saved draft sections will be deleted. Published reports are kept.',
      ),
    ).toBeVisible();
    expect(discard).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Keep job' }));
    expect(
      screen.queryByRole('button', { name: 'Discard job permanently' }),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Discard job' }));
    fireEvent.click(screen.getByRole('button', { name: 'Discard job permanently' }));
    await screen.findByRole('heading', { name: 'Job list destination' });
    expect(discard).toHaveBeenCalledTimes(1);
  },
);

it.each(['running', 'completed', 'needs_review'] as const)(
  'does not offer discard for %s jobs',
  async (status) => {
    server.use(http.get('/api/report-jobs/:id', () => HttpResponse.json(reportJob({ status }))));
    mount();
    await screen.findByRole('heading', { name: 'Researching the available evidence' });
    expect(screen.queryByRole('button', { name: 'Discard job' })).not.toBeInTheDocument();
  },
);

it('clears the discard confirmation on access change and suppresses late navigation after logout', async () => {
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let deletes = 0;
  server.use(
    http.get('/api/report-jobs/:id', () => HttpResponse.json(reportJob({ status: 'paused' }))),
    http.delete('/api/report-jobs/:id', async () => {
      deletes++;
      await gate;
      return new HttpResponse(null, { status: 204 });
    }),
  );
  mount();
  fireEvent.click(await screen.findByRole('button', { name: 'Discard job' }));
  act(() => invalidateWorkspaceAccess());
  await screen.findByRole('button', { name: 'Discard job' });
  expect(screen.queryByRole('button', { name: 'Discard job permanently' })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Discard job' }));
  fireEvent.click(screen.getByRole('button', { name: 'Discard job permanently' }));
  await waitFor(() => expect(deletes).toBe(1));
  act(() => useAuthStore.getState().clearSession());
  await act(async () => {
    release();
    await gate;
  });
  expect(screen.queryByRole('heading', { name: 'Job list destination' })).not.toBeInTheDocument();
  expect(screen.queryByText('Researching the available evidence')).not.toBeInTheDocument();
});
