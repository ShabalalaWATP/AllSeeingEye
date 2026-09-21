import { screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import type { SubscriptionEdition } from '@/lib/api/subscriptionEditions';
import { schedule } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const edition: SubscriptionEdition = {
  id: 'c1c1c1c1-c1c1-41c1-81c1-c1c1c1c1c1c1',
  subscription_id: schedule.id,
  trigger: 'run_now',
  due_at_utc: null,
  frozen_revision: 1,
  requested: { start: '2026-09-21T06:00:00Z', end: '2026-09-22T06:00:00Z' },
  effective_intervals: [],
  gaps: [],
  workflow: 'blocked',
  report_quality: 'absent',
  coverage: 'unknown',
  job_id: null,
  report_id: null,
  version_id: null,
  accepted_as_baseline: false,
  comparison: null,
  safe_reason: 'research_usage_limit',
  created_at: '2026-09-22T06:00:00Z',
  updated_at: '2026-09-22T06:00:00Z',
};

describe('subscription run-now admission', () => {
  it.each([
    {
      workflow: 'blocked',
      reason: 'research_usage_limit',
      notice: /The subscription owner's research allowance is used/,
    },
    {
      workflow: 'blocked',
      reason: 'monthly_budget_exhausted',
      notice: /The monthly AI provider budget is used/,
    },
    {
      workflow: 'pending',
      reason: 'capacity_wait',
      notice: /This edition is waiting for queue space/,
    },
  ] as const)(
    'explains $reason and retries the same unadmitted edition before starting a new one',
    async ({ workflow, reason, notice }) => {
      const requestIds: string[] = [];
      server.use(
        http.post('/api/schedules/:id/run-now', async ({ request }) => {
          const body = (await request.json()) as { request_id: string };
          requestIds.push(body.request_id);
          return HttpResponse.json(
            requestIds.length === 1
              ? { ...edition, workflow, safe_reason: reason }
              : {
                  ...edition,
                  workflow: 'queued',
                  safe_reason: null,
                  job_id: 'd2d2d2d2-d2d2-42d2-82d2-d2d2d2d2d2d2',
                },
          );
        }),
      );
      const { user } = renderApp('/research/recurring', 'user');
      const run = async () => {
        const button = await screen.findByRole('button', { name: 'Run now' });
        await waitFor(() => expect(button).toBeEnabled());
        await user.click(button);
      };
      await run();
      expect(await screen.findByText(notice)).toBeVisible();
      expect(screen.queryByText(/A new report has been queued/)).not.toBeInTheDocument();
      await run();
      expect(await screen.findByText(/A new report has been queued/)).toBeVisible();
      expect(requestIds).toHaveLength(2);
      expect(requestIds[1]).toBe(requestIds[0]);
      await run();
      await waitFor(() => expect(requestIds).toHaveLength(3));
      expect(requestIds[2]).not.toBe(requestIds[1]);
    },
  );
});
