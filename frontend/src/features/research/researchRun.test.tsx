import { jobId, reportJob } from '@/test/reportJobFixture';
import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import type { ReportJobCreate } from '@/lib/api/reportJobs';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('research job submission integration', () => {
  it('sends an idempotency identifier, stops waiting without cancelling the job and suppresses late navigation', async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const submissions: ReportJobCreate[] = [];
    let controls = 0;
    let submissionSignal: AbortSignal | undefined;
    server.use(
      http.post('/api/report-jobs', async ({ request }) => {
        submissions.push((await request.json()) as ReportJobCreate);
        submissionSignal = request.signal;
        await gate;
        return HttpResponse.json(reportJob(), { status: 202 });
      }),
      http.post('/api/report-jobs/:id/:action', () => {
        controls += 1;
        return HttpResponse.json(reportJob());
      }),
    );
    const { user, router } = renderApp('/research', 'user');
    await user.type(await screen.findByLabelText('Your question'), 'What changed?');
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    await waitFor(() => expect(submissions).toHaveLength(1));
    expect(submissions[0]?.request_id).toMatch(/^[0-9a-f-]{36}$/);
    expect(submissions[0]?.report.question).toBe('What changed?');
    await user.click(screen.getByRole('button', { name: 'Stop waiting' }));
    expect(await screen.findByText(/The job may already be running/)).toBeVisible();
    expect(
      within(screen.getByRole('region', { name: 'Research progress' })).getByRole('link', {
        name: 'Research jobs',
      }),
    ).toHaveAttribute('href', '/research/jobs');
    expect(submissionSignal?.aborted).toBe(true);
    expect(controls).toBe(0);
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Start research' })).toBeEnabled(),
    );
    await act(async () => {
      release();
      await gate;
    });
    expect(router.state.location.pathname).toBe('/research');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Your question')).toHaveValue('What changed?');
    await user.clear(screen.getByLabelText('Your question'));
    await user.type(screen.getByLabelText('Your question'), 'What changed in a different area?');
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    await waitFor(() => expect(router.state.location.pathname).toBe(`/research/jobs/${jobId}`));
    expect(submissions).toHaveLength(2);
    expect(submissions[1]?.request_id).not.toBe(submissions[0]?.request_id);
    expect(controls).toBe(0);
  });

  it('retries the original submission with its exact scope and UUID after the question is edited', async () => {
    const submissions: ReportJobCreate[] = [];
    server.use(
      http.post('/api/report-jobs', async ({ request }) => {
        submissions.push((await request.json()) as ReportJobCreate);
        if (submissions.length === 1)
          return HttpResponse.json(
            {
              error: { code: 'unavailable', message: 'Submission receipt could not be confirmed.' },
            },
            { status: 503 },
          );
        return HttpResponse.json(reportJob(), { status: 202 });
      }),
    );
    const { user, router } = renderApp('/research?country=UA', 'user');
    await user.type(await screen.findByLabelText('Your question'), 'Original research question');
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Start research' })).toBeEnabled(),
    );
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Submission receipt could not be confirmed.',
    );
    await user.clear(screen.getByLabelText('Your question'));
    await user.type(screen.getByLabelText('Your question'), 'Edited question for a different job');
    await user.click(screen.getByRole('button', { name: 'Retry this submission' }));
    await waitFor(() => expect(router.state.location.pathname).toBe(`/research/jobs/${jobId}`));
    expect(submissions).toHaveLength(2);
    expect(submissions[1]).toEqual(submissions[0]);
    expect(submissions[1]?.report).toMatchObject({
      question: 'Original research question',
      countries: ['UA'],
    });
    expect(submissions[1]?.request_id).toMatch(/^[0-9a-f-]{36}$/);
  });
});
