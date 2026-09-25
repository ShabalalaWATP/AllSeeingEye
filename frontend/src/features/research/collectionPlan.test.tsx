import { reportJob, readReportJobRequest } from '@/test/reportJobFixture';
import { act, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import * as planApi from '@/lib/api/researchPlan';
import type { ReportRequest } from '@/lib/api/reports';
import { useAuthStore } from '@/stores/auth';
import { plainUser, report, tokenFor } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { openAdvancedResearch } from '@/test/researchForm';
import { server } from '@/test/server';
import { followUpRequest } from '@/lib/followUpScope';

function preview(input: planApi.ResearchPlanInput): planApi.ResearchPlan {
  return {
    question: input.question,
    time_basis: input.time_basis ?? 'publication',
    since: input.since,
    until: input.until,
    languages: input.languages ?? ['en'],
    mode: input.mode,
    focus: input.focus,
    subject: input.subject ?? null,
    country_iso: input.country_iso ?? null,
    country_isos: input.countries ?? [],
    research_web_search: input.research_web_search,
    request_limit: 8,
    seconds_limit: 20,
    item_limit: 50,
    policy_version: 'test-plan-1',
    model_calls: 0,
    translation_calls: 0,
    replans: 0,
    tasks: (input.time_basis === 'recorded_time'
      ? ['research-aiddata-projects', 'google_news', 'wikipedia']
      : ['google_news', 'wikipedia']
    ).map((id) => ({
      source_id: id,
      source_name:
        id === 'research-aiddata-projects'
          ? 'AidData projects'
          : id === 'google_news'
            ? 'Google News'
            : 'Wikipedia',
      selected:
        input.source_ids === null ||
        input.source_ids === undefined ||
        input.source_ids.includes(id),
      supported: true,
      purpose: 'baseline',
      planned_terms_supported: true,
      language: 'en',
      terms: input.query_variants?.[0]?.terms ?? input.terms ?? [],
      provenance: input.query_variants?.length ? 'operator_supplied_variant' : 'original_terms',
      temporal_scope: 'requested_window',
      spatial_supported: false,
      spatial_scope: 'No area-based collection support.',
    })),
  };
}
function mockPreview(bodies: planApi.ResearchPlanInput[]) {
  server.use(
    http.post('/api/research/runs/plan', async ({ request }) => {
      const input = (await request.json()) as planApi.ResearchPlanInput;
      bodies.push(input);
      return HttpResponse.json(preview(input));
    }),
  );
}
async function openPlan() {
  const result = renderApp('/research?question=What%20changed%3F&country=UA', 'user');
  await screen.findByLabelText('Your question');
  await openAdvancedResearch();
  await result.user.click(screen.getByText('Collection plan (optional)'));
  return result;
}

describe('editable collection plan', () => {
  it('explains runtime model additions while keeping preview a deterministic request', async () => {
    const bodies: planApi.ResearchPlanInput[] = [];
    mockPreview(bodies);
    const { user } = await openPlan();
    expect(screen.getByText(/This preview makes no model calls or source requests/)).toBeVisible();
    expect(
      screen.getByText(/These additions share the existing task and collection limits/),
    ).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
    await screen.findByText('Current preview');
    expect(bodies).toHaveLength(1);
    expect(bodies[0]).not.toHaveProperty('planning');
  });
  it('does not substitute news sources for a deselected historical project source', async () => {
    mockPreview([]);
    let submitted = false;
    server.use(
      http.post('/api/report-jobs', () => {
        submitted = true;
        return HttpResponse.json(reportJob(), { status: 202 });
      }),
    );
    const { user } = await openPlan();
    await user.click(screen.getByText('Scope and sources'));
    await user.click(screen.getByText('Advanced source settings'));
    await user.selectOptions(screen.getByLabelText('Research period'), 'history');
    await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
    await screen.findByText('Current preview');
    await user.click(screen.getByRole('checkbox', { name: 'AidData projects' }));
    await user.click(screen.getByRole('checkbox', { name: 'Google News' }));
    await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
    await screen.findByText('Current preview');
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    expect(submitted).toBe(false);
    expect(await screen.findByRole('alert')).toHaveTextContent('supported selected source');
  });
  it('rejects a historical preview that changes the time policy', async () => {
    server.use(
      http.post('/api/research/runs/plan', async ({ request }) => {
        const input = (await request.json()) as planApi.ResearchPlanInput;
        return HttpResponse.json({ ...preview(input), time_basis: 'publication' });
      }),
    );
    const { user } = await openPlan();
    await user.click(screen.getByText('Scope and sources'));
    await user.click(screen.getByText('Advanced source settings'));
    await user.selectOptions(screen.getByLabelText('Research period'), 'history');
    await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The preview does not match the historical period.',
    );
    expect(screen.queryByText('Current preview')).not.toBeInTheDocument();
  });
  it('keeps historical dates fixed and requires repreview after changing years', async () => {
    const plans: planApi.ResearchPlanInput[] = [];
    let body: ReportRequest | undefined;
    mockPreview(plans);
    server.use(
      http.post('/api/report-jobs', async ({ request }) => {
        body = await readReportJobRequest(request);
        return HttpResponse.json(reportJob(), { status: 202 });
      }),
    );
    const { user } = await openPlan();
    await user.click(screen.getByText('Scope and sources'));
    await user.click(screen.getByText('Advanced source settings'));
    await user.selectOptions(screen.getByLabelText('Research period'), 'history');
    expect(screen.queryByLabelText('Reporting window')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    expect(body).toBeUndefined();
    await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
    await screen.findByText('Current preview');
    expect(plans[0]).toMatchObject({
      time_basis: 'recorded_time',
      source_ids: ['research-aiddata-projects'],
      since: '2000-01-01T00:00:00.000Z',
      until: '2022-01-01T00:00:00.000Z',
    });
    await user.clear(screen.getByLabelText('Last commitment year'));
    await user.type(screen.getByLabelText('Last commitment year'), '2020');
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    expect(body).toBeUndefined();
    await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
    await screen.findByText('Current preview');
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    await waitFor(() =>
      expect(body).toMatchObject({
        research_time_basis: 'recorded_time',
        research_since: plans[1]?.since,
        research_until: plans[1]?.until,
      }),
    );
    expect(body?.window_hours).toBeUndefined();
  });
  it('submits the exact previewed terms, variants and sources and requires a fresh preview after edits', async () => {
    const plans: planApi.ResearchPlanInput[] = [];
    let body: ReportRequest | undefined;
    mockPreview(plans);
    server.use(
      http.post('/api/report-jobs', async ({ request }) => {
        body = await readReportJobRequest(request);
        return HttpResponse.json(reportJob(), { status: 202 });
      }),
    );
    const { user } = await openPlan();
    await user.click(screen.getByLabelText('Supply exact search terms'));
    await user.type(screen.getByLabelText('Original search terms'), 'port closure');
    await user.click(screen.getByText('Language-specific search terms'));
    await user.type(screen.getByLabelText('Search terms: English'), 'harbour disruption');
    await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
    expect(await screen.findByText('Current preview')).toBeVisible();
    expect(plans[0]).toMatchObject({
      terms: ['port closure'],
      query_variants: [{ language: 'en', terms: ['harbour disruption'] }],
      countries: ['UA'],
    });
    expect(Date.parse(plans[0]!.until) - Date.parse(plans[0]!.since)).toBe(72 * 3_600_000);
    await user.click(screen.getByRole('checkbox', { name: 'Wikipedia' }));
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Preview your edited collection plan');
    expect(body).toBeUndefined();
    await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
    expect(await screen.findByText('Current preview')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    await waitFor(() =>
      expect(body).toMatchObject({
        research_source_ids: ['google_news'],
        research_terms: ['port closure'],
        research_query_variants: [{ language: 'en', terms: ['harbour disruption'] }],
      }),
    );
    expect(plans[1]?.source_ids).toEqual(body?.research_source_ids);
  });

  it('keeps an explicitly empty source selection and does not silently reinstate defaults', async () => {
    const plans: planApi.ResearchPlanInput[] = [];
    let body: ReportRequest | undefined;
    mockPreview(plans);
    server.use(
      http.post('/api/report-jobs', async ({ request }) => {
        body = await readReportJobRequest(request);
        return HttpResponse.json(reportJob(), { status: 202 });
      }),
    );
    const { user } = await openPlan();
    await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
    await screen.findByText('Current preview');
    await user.click(screen.getByRole('checkbox', { name: 'Google News' }));
    await user.click(screen.getByRole('checkbox', { name: 'Wikipedia' }));
    expect(screen.getByText(/No public sources selected/)).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
    await screen.findByText('Current preview');
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    await waitFor(() => expect(body?.research_source_ids).toEqual([]));
    expect(body?.research_terms).toBeUndefined();
  });

  it('invalidates the preview when the question changes and preserves edits after an API failure', async () => {
    mockPreview([]);
    const { user } = await openPlan();
    await user.click(screen.getByLabelText('Supply exact search terms'));
    await user.type(screen.getByLabelText('Original search terms'), 'trade');
    await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
    await screen.findByText('Current preview');
    await user.type(screen.getByLabelText('Your question'), ' recently');
    expect(screen.getByText(/Previous preview, settings have changed/)).toBeVisible();
    server.use(
      http.post('/api/research/runs/plan', () =>
        HttpResponse.json(
          { error: { code: 'invalid_request', message: 'Plan unavailable.' } },
          { status: 422 },
        ),
      ),
    );
    await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Plan unavailable.');
    expect(screen.getByLabelText('Original search terms')).toHaveValue('trade');
  });

  it('discards a late preview after the account changes', async () => {
    let release: (value: planApi.ResearchPlan) => void = () => undefined;
    const pending = new Promise<planApi.ResearchPlan>((resolve) => {
      release = resolve;
    });
    const call = vi.spyOn(planApi, 'previewResearchPlan').mockReturnValueOnce(pending);
    const { user } = await openPlan();
    await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
    expect(call).toHaveBeenCalledOnce();
    act(() =>
      useAuthStore
        .getState()
        .setSession(tokenFor({ ...plainUser, id: '99999999-9999-4999-8999-999999999999' })),
    );
    expect(call.mock.calls[0]?.[1].aborted).toBe(true);
    await act(async () => {
      release(preview(call.mock.calls[0]![0]));
      await pending;
    });
    expect(screen.queryByText('Current preview')).not.toBeInTheDocument();
  });

  it('retains explicit frozen scope, including an empty source list and Chinese script', () => {
    const saved = {
      ...report,
      report: {
        ...report.report,
        scope: {
          research_mode: 'quick',
          research_languages: ['fa'],
          report_language: 'zh-Hant',
          research_source_ids: [],
          research_terms: ['بندر'],
          research_query_variants: [{ language: 'fa', terms: ['بندر'] }],
        },
      },
    };
    expect(followUpRequest(saved)).toMatchObject({
      report_language: 'zh-Hant',
      research_source_ids: [],
      research_terms: ['بندر'],
      research_query_variants: [{ language: 'fa', terms: ['بندر'] }],
    });
  });
});
