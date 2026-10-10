import type { components } from '../src/lib/api/types.gen';
import { report } from '../src/test/fixtures.reports';
import { schedule } from '../src/test/fixtures.schedules';

import type { BrowserApi } from './fixture';

export const REPORT_ID = report.report.id;
export const OTHER_REPORT_ID = '99999999-9999-4999-8999-999999999999';
export const FROZEN_TEXT = 'Frozen edition one: the terminal remained closed.';
export const LATEST_TEXT = 'Latest edition two: the terminal has reopened.';

export function serveReports(api: BrowserApi) {
  for (const id of [REPORT_ID, OTHER_REPORT_ID]) {
    api.handlers.set(`GET /api/reports/${id}`, async (route) => {
      const version = new URL(route.request().url()).searchParams.get('version') === '1' ? 1 : 2;
      await route.fulfill({
        json: {
          ...report,
          report: {
            ...report.report,
            id,
            title: id === REPORT_ID ? 'Port editions' : 'Alert destination',
            latest_version: 2,
          },
          version: {
            ...report.version,
            number: version,
            body: {
              ...report.version.body,
              assessment: [
                {
                  heading: 'Edition finding',
                  text: version === 1 ? FROZEN_TEXT : LATEST_TEXT,
                  evidence: ['E1'],
                },
              ],
            },
          },
        },
      });
    });
    api.handlers.set(`GET /api/reports/${id}/team-discussion`, async (route) => {
      await route.fulfill({
        json: { team_id: null, count: 0, latest_post_id: null, can_post: false },
      });
    });
  }
}

const interval = { start: '2026-10-08T06:00:00Z', end: '2026-10-09T06:00:00Z' };
const edition: components['schemas']['SubscriptionEditionOut'] = {
  id: 'c1c1c1c1-c1c1-41c1-81c1-c1c1c1c1c1c1',
  subscription_id: schedule.id,
  trigger: 'scheduled',
  due_at_utc: interval.end,
  frozen_revision: 1,
  requested: interval,
  effective_intervals: [interval],
  gaps: [],
  workflow: 'completed',
  report_quality: 'ready',
  coverage: 'complete_for_plan',
  job_id: null,
  report_id: REPORT_ID,
  version_id: 'e3e3e3e3-e3e3-43e3-83e3-e3e3e3e3e3e3',
  version_number: 1,
  comparison: null,
  safe_reason: null,
  created_at: interval.end,
  updated_at: interval.end,
  covered_by_edition_id: null,
  accepted_as_baseline: false,
};

export function serveSubscription(api: BrowserApi) {
  const responses: Record<string, unknown> = {
    '/api/schedules': { items: [{ ...schedule, last_report_id: REPORT_ID }] },
    '/api/direction/plans': { items: [] },
    [`/api/schedules/${schedule.id}/editions`]: { items: [edition], limit: 10, offset: 0 },
  };
  for (const id of [null, schedule.id]) {
    const path = id === null ? '/api/schedules/usage' : `/api/schedules/${id}/usage`;
    responses[path] = {
      scope: id === null ? 'owner' : 'subscription',
      subscription_id: id,
      month_start: '2026-10-01T00:00:00Z',
      month_end: '2026-11-01T00:00:00Z',
      policy_version: 'subscription-monthly-budget-v1',
      used: { requests: 0, output_tokens: 0 },
      limit: { requests: 240, output_tokens: 8_000_000 },
    };
  }
  for (const [path, json] of Object.entries(responses)) {
    api.handlers.set(`GET ${path}`, async (route) => {
      await route.fulfill({ json });
    });
  }
}
