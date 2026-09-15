import { reportJob, readReportJobRequest } from '@/test/reportJobFixture';
import { act, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { report } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { followUpAvailability, followUpRequest } from './followUpScope';

const area = {
  geometry: {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        id: 0,
        properties: {},
        geometry: {
          type: 'Polygon',
          coordinates: [
            [
              [0, 0],
              [2, 0],
              [2, 2],
              [0, 2],
              [0, 0],
            ],
          ],
        },
      },
    ],
  },
  sha256: 'a'.repeat(64),
};

it('loads the selected older edition and keeps its recorded historical period on submission', async () => {
  const parent = {
    ...report,
    report: {
      ...report.report,
      latest_version: 2,
      scope: {
        research_mode: 'detailed',
        research_focus: 'general',
        research_time_basis: 'recorded_time',
        research_since: '2000-01-01T00:00:00Z',
        research_until: '2021-01-01T00:00:00Z',
        window_hours: 184104,
        research_source_ids: ['research-aiddata-projects'],
      },
    },
    version: {
      ...report.version,
      number: 1,
      period_from: '2000-01-01T00:00:00Z',
      period_to: '2021-01-01T00:00:00Z',
    },
  };
  const fetched: string[] = [];
  let submitted: unknown;
  server.use(
    http.get(`/api/reports/${report.report.id}`, ({ request }) => {
      fetched.push(new URL(request.url).search);
      return HttpResponse.json(parent);
    }),
    http.post('/api/report-jobs', async ({ request }) => {
      submitted = await readReportJobRequest(request);
      return HttpResponse.json(reportJob(), { status: 202 });
    }),
  );
  const { user } = renderApp(`/reports/${report.report.id}?version=1`, 'user');
  const followUp = await screen.findByRole('link', { name: /Ask a follow-up question/ });
  expect(followUp).toHaveAttribute('href', `/research?parent=${report.report.id}&parent_version=1`);
  await user.click(followUp);
  expect(
    await screen.findByText(/Follow-up to Intelligence summary: Ukraine, edition 1/),
  ).toBeVisible();
  expect(screen.getByText(/Parent observation period: 2000-01-01/)).toBeVisible();
  expect(screen.getByText(/Recorded-time period: 2000-01-01/)).toBeVisible();
  await user.type(screen.getByLabelText('Your question'), 'What changed in these projects?');
  await user.click(screen.getByRole('button', { name: 'Start research' }));
  await waitFor(() => expect(submitted).toBeDefined());
  expect(fetched).toEqual(['?version=1', '?version=1']);
  expect(submitted).toMatchObject({
    parent_report_id: report.report.id,
    parent_version: 1,
    research_time_basis: 'recorded_time',
    research_since: '2000-01-01T00:00:00Z',
    research_until: '2021-01-01T00:00:00Z',
    research_source_ids: ['research-aiddata-projects'],
  });
  expect(submitted).not.toHaveProperty('window_hours');
});

it.each(['research_area', 'map_origin'])(
  'keeps exact geometry and recorded period for a %s report',
  (origin) => {
    const request = followUpRequest({
      ...report,
      report: {
        ...report.report,
        scope: {
          research_focus: 'general',
          research_mode: 'detailed',
          research_time_basis: 'recorded_time',
          research_since: '2000-01-01T00:00:00Z',
          research_until: '2021-01-01T00:00:00Z',
          disclose_area_to_provider: true,
          [origin]: origin === 'map_origin' ? { area, revision_id: 'saved' } : area,
        },
      },
    });
    expect(request).toMatchObject({
      parent_version: 1,
      research_area: { geometry: area.geometry },
      research_time_basis: 'recorded_time',
      research_since: '2000-01-01T00:00:00Z',
      research_until: '2021-01-01T00:00:00Z',
      disclose_area_to_provider: true,
    });
    expect(request).not.toHaveProperty('map_view_id');
    expect(request).not.toHaveProperty('window_hours');
  },
);

it('submits an authorised saved-map area as a follow-up with its exact geometry', async () => {
  const parent = {
    ...report,
    report: {
      ...report.report,
      scope: {
        research_focus: 'general',
        research_mode: 'detailed',
        research_time_basis: 'recorded_time',
        research_since: '2000-01-01T00:00:00Z',
        research_until: '2021-01-01T00:00:00Z',
        disclose_area_to_provider: true,
        map_origin: { area, revision_id: 'saved-revision' },
      },
    },
  };
  let submitted: unknown;
  server.use(
    http.get(`/api/reports/${report.report.id}`, () => HttpResponse.json(parent)),
    http.post('/api/report-jobs', async ({ request }) => {
      submitted = await readReportJobRequest(request);
      return HttpResponse.json(reportJob(), { status: 202 });
    }),
  );
  const { user } = renderApp(`/reports/${report.report.id}`, 'user');
  await user.click(await screen.findByRole('link', { name: /Ask a follow-up question/ }));
  expect(await screen.findByText(/exact saved area geometry/)).toBeVisible();
  await user.type(screen.getByLabelText('Your question'), 'Which area projects changed?');
  await user.click(screen.getByRole('button', { name: 'Start research' }));
  await waitFor(() => expect(submitted).toBeDefined());
  expect(submitted).toMatchObject({
    parent_report_id: report.report.id,
    parent_version: 1,
    research_area: { geometry: area.geometry },
    research_time_basis: 'recorded_time',
    research_since: '2000-01-01T00:00:00Z',
    research_until: '2021-01-01T00:00:00Z',
    disclose_area_to_provider: true,
  });
  expect(submitted).not.toHaveProperty('map_view_id');
});

it('offers no broken action for a saved area with missing geometry or interval', async () => {
  const parent = {
    ...report,
    report: {
      ...report.report,
      scope: { ...report.report.scope, research_area: { revision_id: 'saved' } },
    },
  };
  expect(followUpAvailability(parent).reason).toMatch(/saved scope cannot be safely restored/);
  server.use(http.get(`/api/reports/${report.report.id}`, () => HttpResponse.json(parent)));
  const { router } = renderApp(`/reports/${report.report.id}`, 'user');
  expect(await screen.findByText(/Follow-up unavailable:/)).toBeVisible();
  expect(screen.getByRole('button', { name: 'Ask a follow-up question' })).toBeDisabled();
  expect(screen.queryByRole('link', { name: /Ask a follow-up question/ })).not.toBeInTheDocument();
  await act(async () => {
    await router.navigate(`/research?parent=${report.report.id}`);
  });
  expect(await screen.findByText(/Follow-up unavailable:/)).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Start research' })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Retry parent report' })).not.toBeInTheDocument();
});

it('blocks a malformed parent edition link before rendering a research form', async () => {
  renderApp(`/research?parent=${report.report.id}&parent_version=latest`, 'user');
  expect(await screen.findByRole('alert')).toHaveTextContent('valid parent report and edition');
  expect(screen.queryByRole('form', { name: 'Research a question' })).not.toBeInTheDocument();
});

it('refuses a server response for a different edition instead of silently using latest', async () => {
  server.use(http.get(`/api/reports/${report.report.id}`, () => HttpResponse.json(report)));
  renderApp(`/research?parent=${report.report.id}&parent_version=2`, 'user');
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'The selected parent edition could not be loaded.',
  );
  expect(screen.queryByRole('button', { name: 'Start research' })).not.toBeInTheDocument();
});
