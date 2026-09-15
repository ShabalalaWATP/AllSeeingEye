import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { schedule } from '@/test/fixtures';
import { reportJob } from '@/test/reportJobFixture';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import type { BriefDraft, ResearchBrief } from '@/lib/api/researchBriefSchema';
import { newBriefDraft } from '@/lib/researchBriefDraft';

const briefId = 'd73c2988-d2ca-4482-9e39-7269e876eaa0';
const now = '2026-09-14T10:00:00Z';

function brief(draft: BriefDraft, revision = 1): ResearchBrief {
  return {
    ...draft,
    identity: {
      id: briefId,
      revision,
      owner_id: 'd2e73f24-a73a-4ee7-b478-f175a05ba96d',
      team_id: draft.team_id,
      title: draft.title,
      created_at: now,
      revised_at: now,
      preset_id: draft.preset_id,
      preset_version: draft.preset_version,
      schema_version: 1,
      origin: 'authored',
      published: false,
    },
  };
}

it('saves a canonical draft, runs its exact revision and cancels later edits', async () => {
  let posted: BriefDraft | null = null;
  let runBody: unknown;
  server.use(
    http.post('/api/research/briefs', async ({ request }) => {
      posted = (await request.json()) as BriefDraft;
      return HttpResponse.json({ brief: brief(posted) }, { status: 201 });
    }),
    http.get(`/api/research/briefs/${briefId}/revisions/1`, () =>
      HttpResponse.json({ brief: brief(posted ?? newBriefDraft()) }),
    ),
    http.post('/api/report-jobs/from-brief', async ({ request }) => {
      runBody = await request.json();
      return HttpResponse.json(reportJob(), { status: 202 });
    }),
  );
  const { user, router } = renderApp('/research?brief=new', 'user');
  let editor = within(await screen.findByRole('region', { name: 'Research Brief editor' }));
  await user.type(editor.getByLabelText('Brief title'), 'Port intelligence');
  await user.type(editor.getByLabelText('Main research question'), 'What changed at the port?');
  await user.click(editor.getByRole('button', { name: 'Add requirement' }));
  await user.type(editor.getByLabelText('Requirement 1 question'), 'Has throughput changed?');
  await user.click(editor.getByRole('button', { name: 'Save brief' }));
  await waitFor(() => expect(posted).not.toBeNull());
  expect(posted).toMatchObject({
    title: 'Port intelligence',
    question: {
      main: 'What changed at the port?',
      requirements: [
        { id: 'req-1', question: 'Has throughput changed?', required: true, priority: 1 },
      ],
    },
    observation: { policy: 'relative', lookback_hours: 24 },
  });
  await waitFor(() => expect(router.state.location.search).toContain(`brief=${briefId}`));
  // The editor remounts with the saved revision, so query the page rather than a stale region.
  await waitFor(() => expect(screen.getByText(/Exact saved revision 1/)).toBeVisible());
  await waitFor(() =>
    expect(screen.getByRole('heading', { name: 'Review and run' })).toHaveFocus(),
  );
  editor = within(await screen.findByRole('region', { name: 'Research Brief editor' }));
  await user.click(editor.getByRole('button', { name: '1 Brief' }));
  await user.clear(editor.getByLabelText('Brief title'));
  await user.type(editor.getByLabelText('Brief title'), 'Unsaved');
  await user.click(editor.getByRole('button', { name: '4 Run' }));
  expect(editor.getByRole('button', { name: 'Run once' })).toBeDisabled();
  await user.click(editor.getByRole('button', { name: 'Cancel changes' }));
  expect(editor.getByLabelText('Brief title')).toHaveValue('Port intelligence');
  await user.click(editor.getByRole('button', { name: 'Run once' }));
  await waitFor(() => expect(runBody).toMatchObject({ brief_id: briefId, revision: 1 }));
  expect(Object.keys(runBody as object).sort()).toEqual(['brief_id', 'request_id', 'revision']);
});

it('preserves unedited advanced collection, output and private-reference fields on revision', async () => {
  const original = newBriefDraft();
  original.title = 'Advanced source review';
  original.question.main = 'What changed across the sources?';
  original.question.requirements = Array.from({ length: 12 }, (_, index) => ({
    id: `req-${index + 1}`,
    question: `What does source ${index + 1} show?`,
    required: true,
    priority: index + 1,
  }));
  original.question.exclusions = ['Exclude the old claim'];
  original.output.depth = 'advanced';
  original.output.language = 'fr';
  original.output.preferred_sections = ['timeline', 'gaps'];
  original.collection.languages = ['en', 'fr'];
  original.collection.terms = ['port', 'traffic'];
  original.collection.query_variants = [
    {
      language: 'fr',
      terms: ['port'],
      kind: 'translation',
      original_terms: ['port'],
      source_script: null,
      target_script: null,
      method: null,
    },
  ];
  original.collection.candidate_hypotheses = [
    {
      id: 'candidate-1',
      label: 'Port authority',
      identifiers: [],
      origin: 'operator',
      registry_identifiers: [],
    },
  ];
  original.collection.planned_tasks = [
    {
      id: 'task-1',
      source_id: 'public-feed',
      purpose: 'challenge',
      terms: ['port'],
      candidate_id: null,
      origin: 'operator',
      route: 'terms',
      identifier_id: null,
    },
  ];
  original.limits.max_model_calls = 20;
  original.monitoring.indicators = [{ id: 'indicator-1', condition: 'New source added' }];
  original.private_inputs = [
    {
      kind: 'session',
      input_id: 'aab87ced-d5d9-4079-9503-d47d5e23b8f9',
      report_id: null,
      report_version: null,
      expires_at: '2026-10-01T00:00:00Z',
      disclose_to_provider: false,
    },
  ];
  let revised: BriefDraft | null = null;
  server.use(
    http.get(`/api/research/briefs/${briefId}/revisions/2`, () =>
      HttpResponse.json({ brief: brief(original, 2) }),
    ),
    http.post(`/api/research/briefs/${briefId}/revisions`, async ({ request }) => {
      const body = (await request.json()) as BriefDraft & { base_revision: number };
      revised = body;
      return HttpResponse.json({ brief: brief(body, 3) }, { status: 201 });
    }),
  );
  const { user } = renderApp(`/research?brief=${briefId}&revision=2`, 'user');
  const editor = within(await screen.findByRole('region', { name: 'Research Brief editor' }));
  await user.click(editor.getByRole('button', { name: '4 Run' }));
  expect(editor.getByRole('button', { name: 'Subscribe to updates' })).toBeDisabled();
  expect(editor.getByText(/Session files need renewed authority/)).toBeVisible();
  await user.click(editor.getByRole('button', { name: '1 Brief' }));
  await user.clear(editor.getByLabelText('Brief title'));
  await user.type(editor.getByLabelText('Brief title'), 'Revised source review');
  await user.click(editor.getByRole('button', { name: 'Save brief' }));
  await waitFor(() => expect(revised).not.toBeNull());
  expect((revised as BriefDraft | null)?.question.requirements).toEqual(
    original.question.requirements,
  );
  expect((revised as BriefDraft | null)?.question.exclusions).toEqual(original.question.exclusions);
  expect((revised as BriefDraft | null)?.collection).toEqual(original.collection);
  expect((revised as BriefDraft | null)?.output).toEqual(original.output);
  expect((revised as BriefDraft | null)?.limits).toEqual(original.limits);
  expect((revised as BriefDraft | null)?.monitoring).toEqual(original.monitoring);
  expect((revised as BriefDraft | null)?.private_inputs).toEqual(original.private_inputs);
});

it('explains expired private evidence before a run can be started', async () => {
  const original = newBriefDraft();
  original.title = 'Private review';
  original.question.main = 'What does the file show?';
  original.scope.focus = 'document';
  original.private_inputs = [
    {
      kind: 'session',
      input_id: 'aab87ced-d5d9-4079-9503-d47d5e23b8f9',
      report_id: null,
      report_version: null,
      expires_at: '2020-01-01T00:00:00Z',
      disclose_to_provider: false,
    },
  ];
  server.use(
    http.get(`/api/research/briefs/${briefId}/revisions/1`, () =>
      HttpResponse.json({ brief: brief(original) }),
    ),
  );
  const { user } = renderApp(`/research?brief=${briefId}&revision=1`, 'user');
  const editor = within(await screen.findByRole('region', { name: 'Research Brief editor' }));
  await user.click(editor.getByRole('button', { name: '4 Run' }));
  expect(editor.getByRole('button', { name: 'Run once' })).toBeDisabled();
  expect(editor.getByText(/A private input has expired/)).toBeVisible();
  expect(editor.getByRole('link', { name: 'Open Research' })).toHaveAttribute('href', '/research');
});

it('subscribes to the exact saved revision with recurrence only', async () => {
  const original = newBriefDraft();
  original.title = 'Port watch';
  original.question.main = 'What changed at the port?';
  let submitted: Record<string, unknown> | null = null;
  server.use(
    http.get(`/api/research/briefs/${briefId}/revisions/2`, () =>
      HttpResponse.json({ brief: brief(original, 2) }),
    ),
    http.post('/api/schedules/from-brief', async ({ request }) => {
      submitted = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json(
        {
          ...schedule,
          name: 'Port watch',
          brief_id: briefId,
          brief_revision: 2,
          timezone: 'Europe/London',
          local_hour: 8,
          local_minute: 30,
          collection_policy: 'since_last_success',
        },
        { status: 201 },
      );
    }),
  );
  const { user } = renderApp(`/research?brief=${briefId}&revision=2&intent=subscribe`, 'user');
  const form = within(await screen.findByRole('form', { name: 'Subscribe to Research Brief' }));
  expect(form.getByText(/Revision 2/)).toBeVisible();
  await user.clear(form.getByLabelText('IANA timezone'));
  await user.type(form.getByLabelText('IANA timezone'), 'Europe/London');
  fireEvent.change(form.getByLabelText('Local time'), { target: { value: '08:30' } });
  await user.selectOptions(form.getByLabelText('Future collection window'), 'since_last_success');
  await user.click(form.getByRole('button', { name: 'Create subscription' }));
  await waitFor(() => expect(submitted).not.toBeNull());
  expect(submitted).toMatchObject({
    brief_id: briefId,
    brief_revision: 2,
    name: 'Port watch',
    timezone: 'Europe/London',
    local_hour: 8,
    local_minute: 30,
    cadence: 'daily',
    collection_policy: 'since_last_success',
    enabled: true,
  });
  expect(Object.keys(submitted as unknown as Record<string, unknown>).sort()).toEqual([
    'anchor_month',
    'avoid_repetition',
    'brief_id',
    'brief_revision',
    'cadence',
    'collection_policy',
    'enabled',
    'local_hour',
    'local_minute',
    'monthday',
    'name',
    'notify_on_change',
    'timezone',
    'weekday',
  ]);
  expect(await screen.findByText('Subscription created from brief revision 2.')).toBeVisible();
});

it('rejects a mismatched subscription response without claiming success', async () => {
  const original = newBriefDraft();
  original.title = 'Port watch';
  original.question.main = 'What changed at the port?';
  server.use(
    http.get(`/api/research/briefs/${briefId}/revisions/2`, () =>
      HttpResponse.json({ brief: brief(original, 2) }),
    ),
    http.post('/api/schedules/from-brief', () =>
      HttpResponse.json({ ...schedule, brief_id: briefId, brief_revision: 1 }, { status: 201 }),
    ),
  );
  const { user } = renderApp(`/research?brief=${briefId}&revision=2&intent=subscribe`, 'user');
  const form = within(await screen.findByRole('form', { name: 'Subscribe to Research Brief' }));
  await user.click(form.getByRole('button', { name: 'Create subscription' }));
  expect(
    await screen.findByText(/The saved subscription referenced a different brief revision/),
  ).toBeVisible();
  expect(screen.getByRole('link', { name: 'Review subscriptions' })).toBeVisible();
  expect(screen.getByRole('button', { name: 'Subscribe to updates' })).toBeDisabled();
  expect(screen.queryByText('Subscription created from brief revision 2.')).not.toBeInTheDocument();
});
