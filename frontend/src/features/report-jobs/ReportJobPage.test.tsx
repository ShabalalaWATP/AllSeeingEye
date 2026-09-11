import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { Link, MemoryRouter, Route, Routes } from 'react-router';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { applySession } from '@/test/render';
import { reportJob, jobId } from '@/test/reportJobFixture';
import { server } from '@/test/server';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import ReportJobPage from './ReportJobPage';
import ReportJobsPage from './ReportJobsPage';

function mount(path = `/research/jobs/${jobId}`) {
  applySession('user');
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/research/jobs/:id" element={<ReportJobPage />} />
        <Route path="/research/jobs" element={<ReportJobsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

it('shows usable partial sections, selected model and a bounded usage breakdown', async () => {
  server.use(
    http.get('/api/report-jobs/:id', () =>
      HttpResponse.json(reportJob({ status: 'paused', can_resume: true })),
    ),
  );
  mount();
  await screen.findByRole('heading', { name: 'Researching the available evidence' });
  expect(screen.getByText('1 section saved')).toBeVisible();
  expect(screen.getByText(/configured-research-model · Thinking: high/)).toBeVisible();
  expect(screen.getByText(/Saved sections are a working draft/)).toBeVisible();
  fireEvent.click(screen.getByText('Available observations'));
  expect(screen.getByText('A public observation was retained.')).toBeVisible();
  expect(screen.getByText('Coverage remains incomplete.')).toBeVisible();
  expect(screen.getByText('Evidence labels: E1 · E2')).toBeVisible();
  fireEvent.click(screen.getByText('Model, usage and run details'));
  expect(screen.getByText('1,200 of 18,000')).toBeVisible();
});

it('pauses and resumes the same job while retaining accepted sections and warning about uncertain usage', async () => {
  let job = reportJob({ total_sections: 1 });
  const actions: string[] = [];
  server.use(
    http.get('/api/report-jobs/:id', () => HttpResponse.json(job)),
    http.post('/api/report-jobs/:id/:action', ({ params }) => {
      actions.push(String(params.action));
      job = {
        ...job,
        revision: job.revision + 1,
        status: params.action === 'pause' ? 'paused' : 'running',
        stage: params.action === 'pause' ? 'paused' : 'drafting',
        can_resume: params.action === 'pause',
        usage: { ...job.usage, uncertain_calls: 1 },
      };
      return HttpResponse.json(job);
    }),
  );
  const user = userEvent.setup();
  mount();
  const stop = await screen.findByRole('button', { name: 'Stop' });
  expect(screen.getByRole('progressbar', { name: 'Research progress' })).not.toHaveAttribute(
    'value',
  );
  await user.click(stop);
  const resume = await screen.findByRole('button', { name: 'Resume research' });
  expect(screen.getByText(/previous provider call has an unconfirmed outcome/)).toBeVisible();
  expect(screen.getByText('1 section saved')).toBeVisible();
  await user.click(resume);
  await screen.findByRole('button', { name: 'Stop' });
  expect(actions).toEqual(['pause', 'resume']);
  expect(screen.getByText('1 section saved')).toBeVisible();
  expect(screen.getByRole('progressbar', { name: 'Research progress' })).not.toHaveAttribute(
    'value',
  );
});

it('shows a completed report link and offers no resume when the server forbids it', async () => {
  const reportId = '77777777-7777-4777-8777-777777777777';
  server.use(
    http.get('/api/report-jobs/:id', () =>
      HttpResponse.json(
        reportJob({
          status: 'completed',
          stage: 'completed',
          report_id: reportId,
          can_resume: false,
        }),
      ),
    ),
  );
  mount();
  expect(await screen.findByRole('link', { name: /Open completed report/ })).toHaveAttribute(
    'href',
    `/reports/${reportId}`,
  );
  expect(screen.queryByRole('button', { name: 'Resume research' })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Stop' })).not.toBeInTheDocument();
});

it('lists durable jobs and opening or leaving a page never pauses server work', async () => {
  const control = vi.fn(() => HttpResponse.json(reportJob()));
  server.use(
    http.get('/api/report-jobs', () => HttpResponse.json({ items: [reportJob()] })),
    http.post('/api/report-jobs/:id/:action', control),
  );
  const view = mount('/research/jobs');
  const user = userEvent.setup();
  await user.click(await screen.findByRole('link', { name: /Researching the available evidence/ }));
  await screen.findByRole('button', { name: 'Stop' });
  view.unmount();
  expect(control).not.toHaveBeenCalled();
});

it.each(['logout', 'access'] as const)(
  'discards private content and an unfinished control result on %s',
  async (change) => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    let reads = 0;
    server.use(
      http.get('/api/report-jobs/:id', () => {
        reads++;
        return reads === 1
          ? HttpResponse.json(reportJob())
          : HttpResponse.json(
              { error: { code: 'forbidden', message: 'Access changed.' } },
              { status: 403 },
            );
      }),
      http.post('/api/report-jobs/:id/pause', async () => {
        await gate;
        return HttpResponse.json(
          reportJob({ status: 'paused', can_resume: true, title: 'Stale private result' }),
        );
      }),
    );
    mount();
    fireEvent.click(await screen.findByRole('button', { name: 'Stop' }));
    act(() => {
      if (change === 'logout') useAuthStore.getState().clearSession();
      else invalidateWorkspaceAccess();
    });
    expect(screen.queryByText('Researching the available evidence')).not.toBeInTheDocument();
    await act(async () => {
      release();
      await gate;
    });
    await waitFor(() => expect(screen.queryByText('Stale private result')).not.toBeInTheDocument());
    expect(screen.queryByText('Researching the available evidence')).not.toBeInTheDocument();
  },
);

it('switches job identity during a slow control request without blocking the new job or showing the old reply', async () => {
  const nextId = '88888888-8888-4888-8888-888888888888';
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  const controls: string[] = [];
  let nextPaused = false;
  server.use(
    http.get('/api/report-jobs/:id', ({ params }) =>
      HttpResponse.json(
        reportJob({
          id: String(params.id),
          title: params.id === nextId ? 'Next job' : 'Original job',
          status: nextPaused && params.id === nextId ? 'paused' : 'running',
          can_resume: nextPaused && params.id === nextId,
        }),
      ),
    ),
    http.post('/api/report-jobs/:id/pause', async ({ params }) => {
      controls.push(String(params.id));
      if (params.id === jobId) await gate;
      else nextPaused = true;
      return HttpResponse.json(
        reportJob({
          id: String(params.id),
          title: params.id === nextId ? 'Next job' : 'Stale reply',
          status: 'paused',
          can_resume: true,
        }),
      );
    }),
  );
  applySession('user');
  render(
    <MemoryRouter initialEntries={[`/research/jobs/${jobId}`]}>
      <Link to={`/research/jobs/${nextId}`}>Switch job</Link>
      <Routes>
        <Route path="/research/jobs/:id" element={<ReportJobPage />} />
      </Routes>
    </MemoryRouter>,
  );
  fireEvent.click(await screen.findByRole('button', { name: 'Stop' }));
  await waitFor(() => expect(controls).toEqual([jobId]));
  fireEvent.click(screen.getByRole('link', { name: 'Switch job' }));
  await screen.findByRole('heading', { name: 'Next job' });
  fireEvent.click(screen.getByRole('button', { name: 'Stop' }));
  await screen.findByRole('button', { name: 'Resume research' });
  expect(controls).toEqual([jobId, nextId]);
  await act(async () => {
    release();
    await gate;
  });
  expect(screen.getByRole('heading', { name: 'Next job' })).toBeVisible();
  expect(screen.queryByText('Stale reply')).not.toBeInTheDocument();
});
