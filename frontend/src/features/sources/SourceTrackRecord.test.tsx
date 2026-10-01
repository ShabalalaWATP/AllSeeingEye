import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { SourceTrackRecord } from '@/lib/api/sourceTrackRecord';
import { sourceContext } from '@/test/fixtures.researchMetadata';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const record: SourceTrackRecord = {
  source_id: 'bbc_world',
  report_bound: 1000,
  reports_considered: 1000,
  visible_reports: 1240,
  reports_citing: 4,
  frozen_items: 5,
  roles: {
    supporting_judgements: 3,
    contradicting_judgements: 1,
    items_cited_elsewhere: 1,
    items_not_cited: 2,
  },
  reports_by_status: { ready: 3, needs_review: 1, failed: 0 },
  judgements_by_status: { ready: 3, needs_review: 1, failed: 0 },
  reliability: [
    { value: 'B', items: 4 },
    { value: 'C', items: 1 },
  ],
  credibility: [
    { value: '2', items: 3 },
    { value: '4', items: 2 },
  ],
  entries: [
    {
      report_id: '00000000-0000-4000-8000-000000000011',
      title: 'Port activity <b>assessment</b>',
      version_number: 2,
      status: 'needs_review',
      saved_at: '2026-09-28T10:00:00Z',
      items: 2,
      supporting_judgements: 0,
      contradicting_judgements: 1,
      grades: ['B2', 'C4'],
    },
  ],
  entries_total: 4,
  reviews: [
    {
      kind: 'reliability',
      decision: 'A',
      recorded_at: '2026-09-29T09:30:00Z',
      report_id: '00000000-0000-4000-8000-000000000011',
      team_scoped: true,
    },
  ],
  reviews_total: 1,
  citation_verdicts: {
    available: false,
    note: 'Citation verdicts are not recorded yet, so none are shown. Their absence is not a passed check.',
  },
};

function catalogue() {
  server.use(http.get('/api/sources', () => HttpResponse.json({ items: [sourceContext] })));
}

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

describe('source track record', () => {
  it('loads only when opened and shows bounded counts without a score', async () => {
    catalogue();
    let requests = 0;
    server.use(
      http.get('/api/sources/:id/track-record', ({ params }) => {
        requests += 1;
        expect(params.id).toBe('bbc_world');
        return HttpResponse.json(record);
      }),
    );
    const { user } = renderApp('/sources', 'user');
    expect(await screen.findByRole('heading', { name: 'BBC World' })).toBeVisible();
    expect(requests).toBe(0);

    await user.click(screen.getByText('Track record'));
    const panel = await screen.findByRole('region', { name: 'Track record for BBC World' });
    expect(requests).toBe(1);
    expect(
      await within(panel).findByText(/latest 1,000 of your 1,240 visible reports/),
    ).toBeVisible();
    expect(within(panel).getByText(/Cited in 4 reports/)).toBeVisible();
    expect(within(panel).getByText('Supporting a key judgement')).toBeVisible();
    expect(within(panel).getByText('Needs review')).toBeVisible();
    expect(within(panel).getByText('B: 4 items')).toBeVisible();
    expect(within(panel).getByText('4: 2 items')).toBeVisible();
    expect(within(panel).getByText('Port activity <b>assessment</b>')).toBeVisible();
    expect(within(panel).getByRole('link', { name: /Port activity/ })).toHaveAttribute(
      'href',
      '/reports/00000000-0000-4000-8000-000000000011',
    );
    expect(within(panel).getByText(/Showing 1 of 4 citing reports/)).toBeVisible();
    expect(within(panel).getByText(/Reliability A/)).toBeVisible();
    expect(within(panel).getByText(/Team review/)).toBeVisible();
    expect(within(panel).getByText(/Citation verdicts are not recorded yet/)).toBeVisible();
    expect(panel.textContent).not.toMatch(/%|score/i);
    expect(panel.querySelector('b')).toBeNull();

    await user.click(screen.getByText('Track record'));
    await user.click(screen.getByText('Track record'));
    expect(requests).toBe(2);
  });

  it('explains an empty record and reports load errors with a retry', async () => {
    catalogue();
    let requests = 0;
    server.use(
      http.get('/api/sources/:id/track-record', () => {
        requests += 1;
        return requests === 1
          ? apiError(503, 'unavailable', 'Track record unavailable.')
          : HttpResponse.json({
              ...record,
              reports_considered: 3,
              visible_reports: 3,
              reports_citing: 0,
              frozen_items: 0,
              entries: [],
              entries_total: 0,
              reviews: [],
              reviews_total: 0,
              reliability: [],
              credibility: [],
            });
      }),
    );
    const { user } = renderApp('/sources', 'user');
    await screen.findByRole('heading', { name: 'BBC World' });
    await user.click(screen.getByText('Track record'));
    expect(await screen.findByText('Track record unavailable.')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Retry track record' }));
    expect(await screen.findByText(/Not cited in your 3 visible reports/)).toBeVisible();
    expect(screen.getByText('No reviewer decisions recorded.')).toBeVisible();
  });

  it('is not offered in the administration catalogue', async () => {
    catalogue();
    renderApp('/admin/catalogue', 'admin');
    expect(await screen.findByRole('heading', { name: 'BBC World' })).toBeVisible();
    expect(screen.queryByText('Track record')).toBeNull();
  });
});
