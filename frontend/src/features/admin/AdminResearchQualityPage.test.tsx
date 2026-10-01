import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import type {
  QualityJobGroup,
  QualityVersionGroup,
  ResearchQuality,
} from '@/lib/api/researchQuality';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

function versionGroup(
  key: string,
  label: string,
  versions: number,
  extra: Partial<QualityVersionGroup> = {},
): QualityVersionGroup {
  return {
    key,
    label,
    versions,
    ready: versions,
    needs_review: 0,
    failed: 0,
    findings: [],
    receipts: {
      versions_with_receipts: 0,
      versions_without_receipts: versions,
      attempts: 0,
      completed: 0,
      empty: 0,
      unavailable: 0,
      other_unsuccessful: 0,
      versions_with_empty_or_unavailable: 0,
    },
    usage: {
      versions_with_usage: 0,
      versions_without_usage: versions,
      prompt_tokens: 0,
      completion_tokens: 0,
      prompt_tokens_per_version: null,
      completion_tokens_per_version: null,
    },
    ...extra,
  };
}

function jobGroup(key: string, label: string, extra: Partial<QualityJobGroup> = {}) {
  return {
    key,
    label,
    jobs: 4,
    queued: 1,
    running: 0,
    paused: 0,
    completed: 1,
    needs_review: 0,
    failed: 2,
    failed_without_version: 2,
    failed_with_version: 0,
    failure_codes: [{ code: 'model.timeout', jobs: 2 }],
    ...extra,
  } satisfies QualityJobGroup;
}

const overall = versionGroup('all', 'All saved versions', 5, {
  ready: 3,
  needs_review: 1,
  failed: 1,
  findings: [
    { key: 'citation:warning', rule: 'citation', severity: 'warning', versions: 1, occurrences: 2 },
  ],
  receipts: {
    versions_with_receipts: 2,
    versions_without_receipts: 3,
    attempts: 6,
    completed: 2,
    empty: 2,
    unavailable: 2,
    other_unsuccessful: 0,
    versions_with_empty_or_unavailable: 2,
  },
  usage: {
    versions_with_usage: 4,
    versions_without_usage: 1,
    prompt_tokens: 4800,
    completion_tokens: 1200,
    prompt_tokens_per_version: 1200,
    completion_tokens_per_version: 300,
  },
});

const scorecard: ResearchQuality = {
  generated_at: '2026-10-01T09:00:00Z',
  window_days: 90,
  since: '2026-07-03T09:00:00Z',
  versions: {
    bound: 1000,
    in_window: 5,
    counted: 5,
    bound_reached: false,
    overall,
    by_template: [
      versionGroup('intsum', 'Intelligence summary', 4),
      versionGroup('sitrep', 'sitrep', 1),
    ],
    by_depth: [versionGroup('not_recorded', 'Not recorded', 5)],
    by_connection: [versionGroup('p1', 'Offline semantic model', 5)],
  },
  jobs: {
    bound: 1000,
    in_window: 4,
    counted: 4,
    bound_reached: false,
    overall: jobGroup('all', 'All report jobs'),
    by_template: [jobGroup('intsum', 'Intelligence summary')],
    by_depth: [jobGroup('quick', 'quick')],
    by_model: [jobGroup('not_recorded', 'Not recorded')],
  },
  citation_checks: {
    available: false,
    note: 'Citation verdicts are not recorded yet, so no outcomes are counted. Their absence is not a passed check.',
  },
};

describe('AdminResearchQualityPage', () => {
  it('shows each population with its denominator, bound and window', async () => {
    const windows: (string | null)[] = [];
    server.use(
      http.get('/api/admin/research-quality', ({ request }) => {
        windows.push(new URL(request.url).searchParams.get('window_days'));
        return HttpResponse.json(scorecard);
      }),
    );
    const { user } = renderApp('/admin/quality', 'admin');
    expect(
      await screen.findByRole('heading', { name: 'Research quality', level: 1 }),
    ).toBeVisible();
    const nav = screen.getByRole('navigation', { name: 'Administration' });
    expect(within(nav).getByRole('link', { name: 'Research quality' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(await screen.findByText(/5 of 5 saved versions from the last 90 days/)).toBeVisible();
    expect(screen.getByText(/at most the newest 1,000/i)).toBeVisible();
    expect(screen.getByText(/4 of 4 report jobs from the last 90 days/)).toBeVisible();

    const outcomes = screen.getByRole('table', { name: /Saved version outcomes by template/ });
    const row = within(outcomes).getByRole('row', { name: /Intelligence summary/ });
    expect(within(row).getAllByRole('cell')[0]).toHaveTextContent('4');
    expect(within(outcomes).getByRole('row', { name: /All saved versions/ })).toBeVisible();

    await user.click(screen.getByRole('button', { name: 'Depth' }));
    const byDepth = screen.getByRole('table', { name: /Saved version outcomes by depth/ });
    expect(within(byDepth).getByText('Not recorded')).toBeVisible();

    expect(screen.getByText('citation (warning)')).toBeVisible();
    expect(screen.getByText('1 of 5 versions, 2 occurrences')).toBeVisible();
    expect(screen.getByText('2 of 2 versions with receipts')).toBeVisible();
    expect(
      screen.getByText('1,200 prompt and 300 completion tokens per version, from 4 of 5 versions'),
    ).toBeVisible();

    const jobs = screen.getByRole('table', { name: /Report job outcomes by depth/ });
    const jobRow = within(jobs).getByRole('row', { name: /All report jobs/ });
    expect(jobRow).toHaveTextContent('2');
    expect(screen.getByText('model.timeout: 2 of 2 failed jobs')).toBeVisible();
    expect(screen.getByText(/Citation verdicts are not recorded yet/)).toBeVisible();
    expect(screen.getByRole('main').textContent).not.toMatch(/%|score|accuracy/i);

    await user.click(screen.getByRole('button', { name: '30 days' }));
    await screen.findByRole('button', { name: '30 days', pressed: true });
    expect(windows).toEqual(['90', '30']);
  });

  it('says when the version bound is reached', async () => {
    server.use(
      http.get('/api/admin/research-quality', () =>
        HttpResponse.json({
          ...scorecard,
          versions: { ...scorecard.versions, in_window: 1003, counted: 1000, bound_reached: true },
        }),
      ),
    );
    renderApp('/admin/quality', 'admin');
    expect(
      await screen.findByText(/Only the newest 1,000 of 1,003 saved versions are counted/),
    ).toBeVisible();
  });

  it('shows refusals from the server', async () => {
    server.use(
      http.get('/api/admin/research-quality', () =>
        apiError(403, 'forbidden', 'Administrator access is required.'),
      ),
    );
    renderApp('/admin/quality', 'admin');
    expect(await screen.findByRole('alert')).toHaveTextContent('Administrator access is required.');
  });

  it('is not mounted for other accounts', async () => {
    renderApp('/admin/quality', 'user');
    expect(await screen.findByText('Admin access required')).toBeVisible();
    expect(screen.queryByRole('heading', { name: 'Research quality' })).toBeNull();
  });
});
