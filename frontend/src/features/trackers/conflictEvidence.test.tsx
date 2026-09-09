import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { conflictCard, liveEvent } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { ConflictMetrics } from './ConflictMetrics';
import { ConflictEvidenceList } from './ConflictEvidenceList';

it('shows reported ranges and uncertainty without describing a total conflict toll', () => {
  render(
    <ConflictMetrics
      card={{
        ...conflictCard,
        fatalities_upper_7d: 8,
        fatalities_unknown_incidents: 3,
        fatalities_disputed_incidents: 2,
        other_activity_7d: 9,
        unknown_date_reports: 5,
        collapsed_reports_7d: 7,
      }}
    />,
  );
  expect(screen.getByText('4\u20138 reported deaths / 7 d')).toBeInTheDocument();
  expect(screen.getByText('3 incidents with unknown death counts')).toBeInTheDocument();
  expect(screen.getByText('2 incidents with disputed death counts')).toBeInTheDocument();
  expect(screen.getByText('Reported violence')).toBeInTheDocument();
  expect(screen.getByText(/9 other activity reports/)).toBeInTheDocument();
  expect(
    screen.getByText(/5 reports with unknown or imprecise occurrence dates/),
  ).toBeInTheDocument();
  expect(screen.getByText(/7 duplicate or linked reports collapsed/)).toBeInTheDocument();
});

it('renders unknown deaths distinctly from an explicitly reported zero', () => {
  const { rerender } = render(<ConflictMetrics card={{ ...conflictCard, fatalities_7d: null }} />);
  expect(screen.getByText('Reported deaths unknown / 7 d')).toBeInTheDocument();
  expect(screen.queryByText('0 reported deaths / 7 d')).not.toBeInTheDocument();
  rerender(<ConflictMetrics card={{ ...conflictCard, fatalities_7d: 0 }} />);
  expect(screen.getByText('0 reported deaths / 7 d')).toBeInTheDocument();
});

it('shows one representative with expandable related reports, separate dates and native grades', () => {
  const first = liveEvent({
    id: 'primary',
    title: 'Primary account',
    category: 'conflict',
    subtype: 'fight',
    attributes: { occurrence_start: '2026-09-03T10:00:00Z', geo_precision: 2 },
  });
  const second = liveEvent({
    id: 'linked',
    title: 'Related account',
    category: 'conflict',
    subtype: 'fight',
    url: 'javascript:alert(1)',
    attributes: { event_day: 20260903 },
  });
  render(
    <MemoryRouter>
      <ConflictEvidenceList
        events={[first, second]}
        groups={[
          {
            representative_id: first.id,
            report_ids: [first.id, second.id],
            source_ids: ['one', 'two'],
            report_count: 2,
          },
        ]}
      />
    </MemoryRouter>,
  );
  expect(screen.getByText('Primary account')).toBeVisible();
  expect(screen.getByText('Related account')).not.toBeVisible();
  expect(screen.getByText(/independence not established/)).toBeInTheDocument();
  fireEvent.click(screen.getByText('View 1 additional loaded reports'));
  expect(screen.getByText('Related account')).toBeVisible();
  expect(screen.queryByRole('link', { name: 'Related account' })).not.toBeInTheDocument();
  expect(screen.getByText('Occurred: 2026-09-03')).toBeInTheDocument();
  expect(screen.getAllByText(/Published:/)).toHaveLength(2);
  expect(screen.getByText(/source precision 2/)).toBeInTheDocument();
  expect(screen.getAllByText(/Source reliability.*Information credibility/)).toHaveLength(2);
});

it('keeps ungrouped evidence and handles absent representatives and unknown occurrence dates', () => {
  const event = liveEvent({
    id: 'present',
    title: 'Loaded account',
    attributes: { event_day: false },
  });
  render(
    <MemoryRouter>
      <ConflictEvidenceList
        events={[event, event]}
        groups={[
          {
            representative_id: 'missing',
            report_ids: ['missing'],
            source_ids: [],
            report_count: 1,
          },
          {
            representative_id: 'missing',
            report_ids: ['present'],
            source_ids: [],
            report_count: 2,
          },
        ]}
      />
    </MemoryRouter>,
  );
  expect(screen.getAllByText('Loaded account')).toHaveLength(1);
  expect(screen.getByText('Occurred: Unknown')).toBeInTheDocument();
});

it('shows configured collection coverage without implying unavailable sources have no incidents', async () => {
  server.use(
    http.get('/api/trackers/conflict-sources', () =>
      HttpResponse.json({
        items: [
          {
            id: 'ged',
            name: 'UCDP GED',
            role: 'Historical context',
            status: 'healthy',
            detail: 'Published dataset loaded',
            dataset_release: '25.1',
            last_success: '2026-09-08T10:00:00Z',
          },
          {
            id: 'acled',
            name: 'ACLED',
            role: 'Current reporting',
            status: 'not_configured',
            detail: 'Administrator connection required',
            dataset_release: null,
            last_success: null,
          },
          {
            id: 'conflict_screening',
            name: 'AI conflict relevance screening',
            role: 'Relevance screening',
            status: 'waiting',
            detail: 'Waiting for matched source text. Unreviewed signals remain hidden by default.',
            dataset_release: null,
            last_success: null,
          },
        ],
      }),
    ),
  );
  renderApp('/trackers', 'user');
  const panel = await screen.findByRole('region', { name: 'Conflict source coverage' });
  expect(await within(panel).findByText('UCDP GED')).toBeInTheDocument();
  expect(within(panel).getByText('Healthy')).toBeInTheDocument();
  expect(within(panel).getByText('Not configured')).toBeInTheDocument();
  expect(within(panel).getByText(/Dataset 25.1/)).toBeInTheDocument();
  const screening = within(panel).getByText('AI conflict relevance screening').closest('li');
  expect(screening).toHaveTextContent('Waiting for matched source text');
  expect(screening).not.toHaveTextContent('Last successful collection');
  expect(screen.getByText(/No reports collected does not establish absence/)).toBeInTheDocument();
});

it('keeps the board available when optional source status fails and does not echo raw errors', async () => {
  server.use(
    http.get('/api/trackers/conflict-sources', () =>
      HttpResponse.json(
        { error: { code: 'upstream', message: 'PRIVATE-UPSTREAM-ERROR' } },
        { status: 503 },
      ),
    ),
  );
  renderApp('/trackers', 'user');
  expect(await screen.findByRole('table', { name: 'Conflicts' })).toBeInTheDocument();
  expect(await screen.findByText(/Source coverage is temporarily unavailable/)).toBeInTheDocument();
  expect(screen.queryByText('PRIVATE-UPSTREAM-ERROR')).not.toBeInTheDocument();
});
