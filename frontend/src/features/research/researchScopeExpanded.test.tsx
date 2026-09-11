import { fireEvent, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import type { ReportRequest } from '@/lib/api/reports';
import type { ResearchPlanInput } from '@/lib/api/researchPlan';
import { report } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { followUpRequest } from './followUpScope';
import { researchDateError } from './ResearchTimeScope';

function captureRequest() {
  let body: ReportRequest | undefined;
  server.use(
    http.post('/api/reports', async ({ request }) => {
      body = (await request.json()) as ReportRequest;
      return HttpResponse.json(report, { status: 201 });
    }),
  );
  return () => body;
}

it('sends multiple selected countries, a two-year window and the explicit web-search choice', async () => {
  const body = captureRequest();
  const { user } = renderApp('/research?country=UA&question=Compare%20recent%20events', 'user');
  await screen.findByLabelText('Your question');
  await user.click(screen.getByText('Choose countries'));
  await user.type(screen.getByLabelText('Search countries'), 'United');
  await user.click(screen.getByRole('checkbox', { name: /United Kingdom/ }));
  expect(screen.getByRole('button', { name: 'Remove Ukraine' })).toBeVisible();
  expect(screen.getByRole('button', { name: 'Remove United Kingdom' })).toBeVisible();
  await user.selectOptions(screen.getByLabelText('Reporting window'), '17520');
  await user.click(screen.getByRole('checkbox', { name: /Fresh web search/ }));
  await user.click(screen.getByRole('button', { name: 'Start research' }));
  await waitFor(() =>
    expect(body()).toMatchObject({
      countries: ['UA', 'GB'],
      window_hours: 17520,
      research_web_search: true,
    }),
  );
  expect(body()).not.toHaveProperty('country');
});

it('preserves a custom UTC interval without silently reverting to a rolling window', async () => {
  const body = captureRequest();
  const { user } = renderApp('/research?question=Review%20this%20period', 'user');
  await screen.findByLabelText('Your question');
  await user.selectOptions(screen.getByLabelText('Reporting window'), 'custom');
  fireEvent.change(screen.getByLabelText('Start date (UTC)'), {
    target: { value: '2025-01-01T12:00' },
  });
  fireEvent.change(screen.getByLabelText('End date (UTC, exclusive)'), {
    target: { value: '2025-05-01T12:00' },
  });
  await user.click(screen.getByRole('button', { name: 'Start research' }));
  await waitFor(() =>
    expect(body()).toMatchObject({
      countries: [],
      research_since: '2025-01-01T12:00:00Z',
      research_until: '2025-05-01T12:00:00Z',
    }),
  );
  expect(body()).not.toHaveProperty('window_hours');
});

it('removes public-web disclosure when switching to a private attachment', async () => {
  const { user } = renderApp('/research', 'user');
  await screen.findByLabelText('Your question');
  await user.click(screen.getByRole('checkbox', { name: /Fresh web search/ }));
  await user.selectOptions(screen.getByLabelText('Research focus'), 'document');
  expect(screen.queryByRole('checkbox', { name: /Fresh web search/ })).not.toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText('Research focus'), 'general');
  expect(screen.getByRole('checkbox', { name: /Fresh web search/ })).not.toBeChecked();
});

it('previews the same countries, dates and web choice that will be collected', async () => {
  let preview: ResearchPlanInput | undefined;
  server.use(
    http.post('/api/research/runs/plan', async ({ request }) => {
      preview = (await request.json()) as ResearchPlanInput;
      return HttpResponse.json({
        ...preview,
        subject: null,
        country_iso: null,
        country_isos: preview.countries,
        tasks: [
          {
            source_id: 'recent',
            source_name: 'Recent feed',
            selected: true,
            supported: false,
            language: 'en',
            terms: [],
            provenance: 'original_terms',
            temporal_scope: 'Recent observations only, at most 14 days.',
          },
        ],
        request_limit: 6,
        seconds_limit: 45,
        item_limit: 200,
        policy_version: 'fixture',
        model_calls: 0,
        translation_calls: 0,
        replans: 0,
      });
    }),
  );
  const { user } = renderApp('/research?country=UA&question=Review%20this%20period', 'user');
  await screen.findByLabelText('Your question');
  await user.selectOptions(screen.getByLabelText('Reporting window'), 'custom');
  fireEvent.change(screen.getByLabelText('Start date (UTC)'), {
    target: { value: '2025-01-01T12:00' },
  });
  fireEvent.change(screen.getByLabelText('End date (UTC, exclusive)'), {
    target: { value: '2025-05-01T12:00' },
  });
  await user.click(screen.getByRole('checkbox', { name: /Fresh web search/ }));
  await user.click(screen.getByText('Collection plan (optional)'));
  await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
  await screen.findByText('Current preview');
  expect(preview).toMatchObject({
    countries: ['UA'],
    since: '2025-01-01T12:00:00.000Z',
    until: '2025-05-01T12:00:00.000Z',
    research_web_search: true,
  });
  expect(screen.getByText(/Recent observations only, at most 14 days/)).toBeVisible();
  expect(screen.getByText(/Unavailable for these preview inputs/)).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Use worldwide' }));
  expect(screen.getByText('Previous preview, settings have changed')).toBeVisible();
});

it('keeps plural countries, fixed dates and web disclosure immutable in a follow-up', () => {
  const request = followUpRequest({
    ...report,
    report: {
      ...report.report,
      scope: {
        countries: ['GB', 'UA'],
        country: null,
        window_hours: 0,
        research_since: '2025-01-01T00:00:00Z',
        research_until: '2025-01-01T00:30:00Z',
        research_web_search: true,
      },
    },
  });
  expect(request).toMatchObject({
    countries: ['GB', 'UA'],
    research_since: '2025-01-01T00:00:00Z',
    research_until: '2025-01-01T00:30:00Z',
    research_web_search: true,
  });
  expect(request).not.toHaveProperty('window_hours');
  expect(
    followUpRequest({ ...report, report: { ...report.report, scope: { country: 'GB' } } })
      .countries,
  ).toEqual(['GB']);
});

it.each([
  { countries: ['GB', 'GB'] },
  { countries: ['GB'], country: 'UA' },
  { countries: ['GB'], country_isos: ['UA'] },
  { countries: [''] },
  { research_since: '2025-01-01T00:00:00Z' },
  { research_focus: 'document', research_web_search: true },
])('rejects unsafe stored scope rather than widening a follow-up: %j', (scope) => {
  expect(() => followUpRequest({ ...report, report: { ...report.report, scope } })).toThrow();
});

it('rejects reversed, future and overlong dates while accepting exactly 730 days', () => {
  const now = Date.parse('2026-09-11T12:00:00Z');
  const end = new Date(now).toISOString();
  expect(
    researchDateError({ since: new Date(now - 730 * 86_400_000).toISOString(), until: end }, now),
  ).toBeNull();
  expect(
    researchDateError({ since: new Date(now - 731 * 86_400_000).toISOString(), until: end }, now),
  ).toMatch(/730 days/);
  expect(researchDateError({ since: end, until: end }, now)).toMatch(/after the start/);
  expect(
    researchDateError({ since: end, until: new Date(now + 60_000).toISOString() }, now),
  ).toMatch(/future/);
});
