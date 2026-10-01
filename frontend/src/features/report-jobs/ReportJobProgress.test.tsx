import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { http, HttpResponse } from 'msw';
import { afterEach, expect, it, vi } from 'vitest';
import type { ReportJob } from '@/lib/api/reportJobs';
import { applySession } from '@/test/render';
import { jobId, reportJob } from '@/test/reportJobFixture';
import { server } from '@/test/server';
import ReportJobPage from './ReportJobPage';

afterEach(() => vi.useRealTimers());

function show(job: ReportJob) {
  server.use(http.get('/api/report-jobs/:id', () => HttpResponse.json(job)));
  applySession('user');
  render(
    <MemoryRouter initialEntries={[`/research/jobs/${jobId}`]}>
      <Routes>
        <Route path="/research/jobs/:id" element={<ReportJobPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

it('shows determinate section progress with its stage, status and queue-inclusive timer', async () => {
  vi.useFakeTimers({ toFake: ['Date'], now: new Date('2026-09-11T10:12:00Z') });
  show(reportJob({ completed_sections: 2, total_sections: 5 }));
  const bar = await screen.findByRole('progressbar', { name: 'Sections completed' });
  expect(bar).toHaveAttribute('value', '2');
  expect(bar).toHaveAttribute('max', '5');
  expect(screen.getByText('2 of 5 sections saved')).toBeVisible();
  expect(screen.getByRole('status')).toHaveTextContent('Writing sections');
  expect(screen.getByText('In progress')).toBeVisible();
  expect(screen.getByText(/Started 12m ago, including any time queued/)).toBeVisible();
});

it('keeps an unknown total indeterminate without inventing a fraction', async () => {
  show(reportJob({ completed_sections: 0, total_sections: 0, stage: 'collecting' }));
  const bar = await screen.findByRole('progressbar', { name: 'Research progress' });
  expect(bar).not.toHaveAttribute('value');
  expect(screen.getByText('Section count not known yet')).toBeVisible();
  expect(screen.queryByText(/of 0 sections/)).not.toBeInTheDocument();
});

it('stops the running timer once work has stopped', async () => {
  show(
    reportJob({
      status: 'failed',
      stage: 'drafting',
      completed_sections: 1,
      total_sections: 4,
      updated_at: '2026-09-11T10:20:00Z',
    }),
  );
  expect(await screen.findByText('1 of 4 sections saved')).toBeVisible();
  expect(screen.queryByText(/including any time queued/)).not.toBeInTheDocument();
  expect(screen.getByText(/Last updated 11 Sept 2026, 10:20 UTC/)).toBeVisible();
});

it('labels an automatic briefing job as such', async () => {
  show(reportJob({ origin: 'briefing', title: 'Daily briefing' }));
  expect(await screen.findByText('Automatic briefing')).toBeVisible();
});
