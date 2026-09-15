import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { newBriefDraft } from '@/lib/researchBriefDraft';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const briefId = 'd73c2988-d2ca-4482-9e39-7269e876eaa0';
const now = '2026-09-14T10:00:00Z';
const original = {
  ...newBriefDraft(),
  title: 'Port watch',
  scope: {
    ...newBriefDraft().scope,
    country_isos: ['GB'],
    origin_report_id: '11111111-1111-4111-8111-111111111111',
    origin_version: 1,
  },
  observation: { ...newBriefDraft().observation, lookback_hours: 168, forecast_horizon_days: 30 },
  collection: {
    ...newBriefDraft().collection,
    source_policy: 'selected_only',
    source_ids: ['public-feed', 'disabled-feed'],
  },
  output: { ...newBriefDraft().output, depth: 'detailed' },
  question: {
    main: 'What changed at the port?',
    requirements: [
      { id: 'port.q1', question: 'Did traffic change?', required: true, priority: 1 },
      { id: 'port.q2', question: 'What contrary evidence exists?', required: true, priority: 2 },
    ],
    exclusions: [],
  },
};
const saved = {
  ...original,
  identity: {
    id: briefId,
    revision: 3,
    owner_id: 'd2e73f24-a73a-4ee7-b478-f175a05ba96d',
    team_id: null,
    title: 'Port watch',
    created_at: now,
    revised_at: now,
    preset_id: null,
    preset_version: null,
    schema_version: 1,
    origin: 'authored',
    published: false,
  },
};
const preflight = {
  brief_id: briefId,
  revision: 3,
  title: 'Port watch',
  as_of: now,
  scope: {
    country_isos: ['GB'],
    focus: 'general',
    subject: null,
    area_sha256: null,
    saved_map_resolution_required: false,
    linked_context_checks_required: true,
  },
  since: '2026-09-07T10:00:00Z',
  until: now,
  observation_policy: 'relative',
  time_basis: 'publication',
  forecast_horizon_days: 30,
  question: original.question.main,
  requirements: original.question.requirements,
  budget: {
    tier: 'detailed',
    required_question_ceiling: 6,
    tier_source_operations: 24,
    tier_collection_seconds: 180,
    source_operation_ceiling: 24,
    collection_second_ceiling: 180,
    model_call_ceiling: 24,
    output_token_ceiling: 256000,
    reservations_made: false,
  },
  source_policy: 'selected_only',
  sources: [
    {
      capability: {
        id: 'public-feed',
        name: 'Public feed',
        route: 'public_research',
        support: { constraints: 'Publication dates only.' },
      },
      readiness: 'public_unverified',
      candidate_unverified: true,
      exclusion_reasons: [],
      date_note: 'No archive completeness guarantee.',
    },
    {
      capability: {
        id: 'disabled-feed',
        name: 'Disabled feed',
        route: 'public_research',
        support: { constraints: 'Current snapshot only.' },
      },
      readiness: 'disabled',
      candidate_unverified: false,
      exclusion_reasons: ['disabled'],
      date_note: 'No historical coverage.',
    },
  ],
  unknown_source_ids: [],
  gaps: [
    { id: 'gap.original_passages', name: 'Original passages', reason: 'No implemented route.' },
  ],
  candidate_provider_ids: ['public-feed'],
  known_origin_group_count: 1,
  unknown_origin_capability_count: 0,
  review_reasons: ['linked_context_authorisation_not_checked'],
  preview_only: true,
  admission_checked: false,
  source_relevance_ranked: false,
  provider_calls: 0,
  model_calls: 0,
  model_compatibility: 'not_checked',
  policy_version: 'ase-source-capabilities-v1',
  duration_note: 'Collection allowance plus generation time varies.',
  coverage_note: 'No source connectivity or capacity was tested.',
};

it('previews an exact saved revision on keyboard action without starting research', async () => {
  let previewCalls = 0;
  let jobCalls = 0;
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  server.use(
    http.get(`/api/research/briefs/${briefId}/revisions/3`, () =>
      HttpResponse.json({ brief: saved }),
    ),
    http.get(`/api/research/briefs/${briefId}/revisions/3/preflight`, async () => {
      previewCalls += 1;
      await gate;
      return HttpResponse.json({ preflight });
    }),
    http.post('/api/report-jobs/from-brief', () => {
      jobCalls += 1;
      return HttpResponse.json({});
    }),
  );
  const { user } = renderApp(`/research?brief=${briefId}&revision=3`, 'user');
  const editor = within(await screen.findByRole('region', { name: 'Research Brief editor' }));
  await user.click(editor.getByRole('button', { name: '3 Depth' }));
  const button = editor.getByRole('button', { name: 'Preview saved brief' });
  expect(previewCalls).toBe(0);
  button.focus();
  await user.keyboard('{Enter}');
  expect(await screen.findByText('Checking saved brief')).toBeVisible();
  expect(button).toBeDisabled();
  release();
  const result = within(await screen.findByRole('region', { name: 'Saved brief preflight' }));
  expect(result.getByText('Preflight: revision 3')).toBeVisible();
  expect(result.getByText(/2026-09-07 10:00 UTC to 2026-09-14 10:00 UTC/)).toBeVisible();
  expect(result.getByText(/30-day forecast horizon/)).toBeVisible();
  expect(result.getByText(/2 required of 2 selected/)).toBeVisible();
  expect(result.getByText(/up to 6 required questions/)).toBeVisible();
  expect(result.getByText(/No provider or model calls were made/)).toBeVisible();
  expect(result.getByText(/No capacity was reserved/)).toBeVisible();
  expect(result.getByText(/Original passages/)).toBeVisible();
  expect(result.getByText(/linked context authorisation not checked/)).toBeVisible();
  await user.click(result.getByText(/Inspect 2 source routes and exclusions/));
  expect(result.getByText(/Excluded: disabled/)).toBeVisible();
  expect(previewCalls).toBe(1);
  expect(jobCalls).toBe(0);
  await user.click(editor.getByRole('button', { name: '1 Brief' }));
  await user.clear(editor.getByLabelText('Brief title'));
  await user.type(editor.getByLabelText('Brief title'), 'Unsaved title');
  await user.click(editor.getByRole('button', { name: '3 Depth' }));
  expect(screen.queryByRole('region', { name: 'Saved brief preflight' })).not.toBeInTheDocument();
  expect(editor.getByRole('button', { name: 'Preview saved brief' })).toBeDisabled();
  expect(editor.getByText('Save a new revision to preview these edits.')).toBeVisible();
});

it('shows an actionable retry when read-only preflight fails', async () => {
  let attempts = 0;
  server.use(
    http.get(`/api/research/briefs/${briefId}/revisions/3`, () =>
      HttpResponse.json({ brief: saved }),
    ),
    http.get(`/api/research/briefs/${briefId}/revisions/3/preflight`, () => {
      attempts += 1;
      return attempts === 1
        ? HttpResponse.json(
            {
              error: {
                code: 'temporarily_unavailable',
                message: 'Preview is temporarily unavailable.',
              },
            },
            { status: 503 },
          )
        : HttpResponse.json({ preflight });
    }),
  );
  const { user } = renderApp(`/research?brief=${briefId}&revision=3`, 'user');
  await user.click(await screen.findByRole('button', { name: '3 Depth' }));
  const region = within(await screen.findByRole('region', { name: 'Research preflight' }));
  await user.click(region.getByRole('button', { name: 'Preview saved brief' }));
  expect(await region.findByText('Preview is temporarily unavailable.')).toBeVisible();
  await user.click(region.getByRole('button', { name: 'Retry preview' }));
  await waitFor(() => expect(attempts).toBe(2));
  expect(await region.findByRole('region', { name: 'Saved brief preflight' })).toBeVisible();
});
