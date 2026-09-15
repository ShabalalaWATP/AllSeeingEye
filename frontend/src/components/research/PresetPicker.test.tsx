import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { newBriefDraft } from '@/lib/researchBriefDraft';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { savedMapFixture } from '@/test/fixtures.savedMaps';

const groups = ['conflict', 'cyber', 'economy', 'cross_cutting'] as const;
const presetId = 'conflict-global';
const mapId = '7152e032-1be9-4295-8a52-d7c63db09de4';
const mapRevision = 'd00875f8-f58c-4f6c-851d-a596925c15a9';

function item(index: number) {
  const group = groups[Math.floor(index / 5)]!;
  const id = index === 0 ? presetId : `${group}-${index}`;
  const requirements = Array.from({ length: index === 0 ? 4 : 1 }, (_, n) => ({
    id: `${id}.q${n + 1}`,
    question: `What does requirement ${n + 1} show?`,
    required: true,
    priority: n + 1,
  }));
  return {
    preset: {
      id,
      version: 1,
      title: index === 0 ? 'Global conflict briefing' : `${group} starter ${index}`,
      purpose: index === 0 ? 'Evidence on global conflict changes.' : `Review ${group} changes.`,
      group,
      reviewed_on: '2026-09-14',
      question: 'What changed?',
      requirements,
      required_inputs:
        index === 0
          ? [
              {
                id: 'actor',
                label: 'Actor',
                guidance: 'Name the actor to assess.',
                target: 'scope.subject',
                required: true,
              },
            ]
          : [],
      scope_note: 'Review selected scope.',
      suggested_languages: ['en'],
      language_note: 'Language route is unverified.',
      source_bundles: ['NEWS'],
      lens_choices: ['general', 'actor_perspective'],
      default_lens: 'general',
      default_depth: 'detailed',
      keywords: index === 0 ? ['war', 'security'] : [group],
    },
    readiness: {
      policy_version: 'ase-source-capabilities-v1',
      source_bundles: [
        {
          id: 'NEWS',
          candidate_provider_ids: ['public-feed'],
          gap_ids: ['gap.network_telemetry'],
          status: 'unverified_candidates',
        },
      ],
      sources: [
        {
          id: 'public-feed',
          name: 'Public feed',
          readiness: 'public_unverified',
          candidate: true,
          scope_language_compatible: true,
          constraints: 'Publication-date route only.',
          limitations: ['No archive guarantee.'],
        },
      ],
      gaps: [
        {
          id: 'gap.network_telemetry',
          name: 'Network telemetry',
          reason: 'No implemented source route.',
        },
      ],
      languages: [
        {
          language: 'en',
          status: 'configured_route_unverified',
          source_ids: ['public-feed'],
          note: 'Query language only.',
        },
      ],
      candidate_provider_ids: ['public-feed'],
      source_selection_required: false,
      required_input_ids: index === 0 ? ['actor'] : [],
      note: 'Candidates are unverified; no source has been queried.',
    },
  };
}

function catalogue() {
  return {
    schema_version: 1,
    items: Array.from({ length: 20 }, (_, index) => item(index)),
    lens_choices: ['general', 'actor_perspective'],
    lens_rule: 'A lens changes relevance only; evidence rules do not change.',
  };
}

it('shows all 20 grouped presets and filters them with a keyboard-accessible search', async () => {
  let definitionCalls = 0;
  server.use(
    http.get('/api/research/presets', () => HttpResponse.json(catalogue())),
    http.post('/api/research/presets/:id/definition', () => {
      definitionCalls += 1;
      return HttpResponse.json(
        { error: { code: 'unexpected', message: 'Unexpected request' } },
        { status: 500 },
      );
    }),
  );
  const { user } = renderApp('/research?brief=new', 'user');
  await user.click(await screen.findByRole('button', { name: 'Browse presets' }));
  const library = within(await screen.findByRole('region', { name: 'Research preset library' }));
  expect(library.getAllByRole('button', { name: /starter|briefing/i })).toHaveLength(20);
  expect(library.getByRole('region', { name: 'Conflict presets' })).toBeVisible();
  expect(library.getByRole('region', { name: 'Cyber presets' })).toBeVisible();
  expect(library.getByRole('region', { name: 'Economy presets' })).toBeVisible();
  expect(library.getByRole('region', { name: 'Cross-cutting presets' })).toBeVisible();
  await user.selectOptions(library.getByLabelText('Preset group'), 'economy');
  expect(library.getAllByRole('button', { name: /starter|briefing/i })).toHaveLength(5);
  await user.selectOptions(library.getByLabelText('Preset group'), 'all');
  await user.type(library.getByLabelText('Search presets'), 'war');
  expect(library.getAllByRole('button', { name: /starter|briefing/i })).toHaveLength(1);
  const choice = library.getByRole('button', { name: 'Global conflict briefing' });
  choice.focus();
  await user.keyboard('{Enter}');
  expect(choice).toHaveAttribute('aria-pressed', 'true');
  expect(library.getByRole('region', { name: 'Selected preset details' })).toBeVisible();
  expect(library.getByText('Network telemetry')).toBeVisible();
  expect(library.getByText(/No implemented source route/)).toBeVisible();
  expect(library.getByText(/Candidates are unverified/)).toBeVisible();
  expect(definitionCalls).toBe(0);
});

it('requires an explicit Basic reduction, applies a pinned editable definition, and saves only on request', async () => {
  let definitionBody: Record<string, unknown> | null = null;
  let savedBody: Record<string, unknown> | null = null;
  const starter = item(0);
  const definition = {
    ...newBriefDraft(),
    title: starter.preset.title,
    preset_id: presetId,
    preset_version: 1,
    question: {
      main: starter.preset.question,
      requirements: starter.preset.requirements.slice(0, 3),
      exclusions: [],
    },
    lens: { ...newBriefDraft().lens, id: 'actor_perspective' },
    output: { ...newBriefDraft().output, depth: 'quick' },
  };
  server.use(
    http.get('/api/research/presets', () => HttpResponse.json(catalogue())),
    http.post(`/api/research/presets/${presetId}/definition`, async ({ request }) => {
      definitionBody = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json({
        definition,
        readiness: starter.readiness,
        omitted_requirement_ids: [`${presetId}.q4`],
        note: 'Editable starter only.',
      });
    }),
    http.post('/api/research/briefs', async ({ request }) => {
      savedBody = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json(
        { error: { code: 'test_stop', message: 'Recorded save.' } },
        { status: 409 },
      );
    }),
  );
  const { user } = renderApp('/research?brief=new', 'user');
  await user.click(await screen.findByRole('button', { name: 'Browse presets' }));
  const library = within(await screen.findByRole('region', { name: 'Research preset library' }));
  await user.click(await library.findByRole('button', { name: 'Global conflict briefing' }));
  expect(
    within(library.getByRole('region', { name: 'Required preset inputs' })).getByText('Actor'),
  ).toBeVisible();
  await user.selectOptions(library.getByLabelText('Preset depth'), 'quick');
  expect(library.getByRole('button', { name: 'Apply preset to draft' })).toBeDisabled();
  expect(library.getByText(/Nothing is removed automatically/)).toBeVisible();
  await user.click(library.getByLabelText(/What does requirement 4 show/));
  await user.selectOptions(library.getByLabelText('Preset lens'), 'actor_perspective');
  await user.click(library.getByRole('button', { name: 'Apply preset to draft' }));
  await waitFor(() => expect(definitionBody).not.toBeNull());
  expect(definitionBody).toMatchObject({
    version: 1,
    depth: 'quick',
    lens: 'actor_perspective',
    selected_requirement_ids: [`${presetId}.q1`, `${presetId}.q2`, `${presetId}.q3`],
  });
  expect(savedBody).toBeNull();
  const editor = within(screen.getByRole('region', { name: 'Research Brief editor' }));
  expect(editor.getByLabelText('Main research question')).toHaveValue('What changed?');
  expect(library.getByText(/Nothing has been saved or run/)).toBeVisible();
  expect(library.getByText(/Still needed/)).toBeVisible();
  await user.click(editor.getByRole('button', { name: '2 Scope' }));
  await user.type(editor.getByLabelText('Research subject'), 'Named actor');
  await user.click(editor.getByRole('button', { name: '1 Brief' }));
  expect(library.getByText(/Provided/)).toBeVisible();
  await user.clear(editor.getByLabelText('Main research question'));
  await user.type(editor.getByLabelText('Main research question'), 'What did the named actor do?');
  await user.click(editor.getByRole('button', { name: 'Save brief' }));
  await waitFor(() => expect(savedBody).not.toBeNull());
  expect(savedBody).toMatchObject({
    preset_id: presetId,
    preset_version: 1,
    question: {
      main: 'What did the named actor do?',
      requirements: definition.question.requirements,
    },
    scope: { subject: 'Named actor' },
    lens: { id: 'actor_perspective' },
    output: { depth: 'quick' },
  });
});

it('keeps an exact saved polygon and selected question when the area starter is applied', async () => {
  const area = {
    ...item(19),
    preset: {
      ...item(19).preset,
      id: 'area-custom',
      title: 'Area research',
      required_inputs: [
        {
          id: 'area',
          label: 'Exact area',
          guidance: 'Choose a saved polygon.',
          target: 'scope.area',
          required: true,
        },
        {
          id: 'question',
          label: 'Main question',
          guidance: 'Replace the starter question.',
          target: 'question.main',
          required: true,
        },
      ],
    },
  };
  const map = {
    ...savedMapFixture,
    view: { ...savedMapFixture.view, id: mapId, latest_revision_id: mapRevision },
    revision: { ...savedMapFixture.revision, id: mapRevision, view_id: mapId },
  };
  server.use(
    http.get(`/api/map/views/${mapId}/revisions/${mapRevision}`, () => HttpResponse.json(map)),
    http.get('/api/research/presets', () => HttpResponse.json({ ...catalogue(), items: [area] })),
    http.post('/api/research/presets/area-custom/definition', () =>
      HttpResponse.json({
        definition: {
          ...newBriefDraft(),
          title: 'Area research',
          preset_id: 'area-custom',
          preset_version: 1,
          question: { main: 'Starter question', requirements: [], exclusions: [] },
        },
        readiness: area.readiness,
        omitted_requirement_ids: [],
        note: 'Editable starter only.',
      }),
    ),
  );
  const { user } = renderApp(
    `/research?brief=new&map_view=${mapId}&map_revision=${mapRevision}&question=What+changed+here%3F`,
    'user',
  );
  await user.click(await screen.findByRole('button', { name: 'Browse presets' }));
  const library = within(await screen.findByRole('region', { name: 'Research preset library' }));
  expect(library.getAllByRole('button', { name: 'Area research' })).toHaveLength(1);
  await user.click(library.getByRole('button', { name: 'Area research' }));
  await user.click(library.getByRole('button', { name: 'Apply preset to draft' }));
  const editor = within(screen.getByRole('region', { name: 'Research Brief editor' }));
  await waitFor(() =>
    expect(editor.getByLabelText('Main research question')).toHaveValue('What changed here?'),
  );
  await user.click(editor.getByRole('button', { name: '2 Scope' }));
  expect(
    editor.getByText(new RegExp(`Exact saved map revision pinned: ${mapRevision}`)),
  ).toBeVisible();
});

it('keeps the draft unchanged when a pinned preset version is rejected', async () => {
  server.use(
    http.get('/api/research/presets', () => HttpResponse.json(catalogue())),
    http.post(`/api/research/presets/${presetId}/definition`, () =>
      HttpResponse.json(
        {
          error: {
            code: 'conflict',
            message: 'The preset version changed. Review it before adopting the update.',
          },
        },
        { status: 409 },
      ),
    ),
  );
  const { user } = renderApp('/research?brief=new', 'user');
  const editor = within(await screen.findByRole('region', { name: 'Research Brief editor' }));
  await user.type(editor.getByLabelText('Main research question'), 'Keep my draft');
  await user.click(editor.getByRole('button', { name: 'Browse presets' }));
  const library = within(await screen.findByRole('region', { name: 'Research preset library' }));
  await user.click(await library.findByRole('button', { name: 'Global conflict briefing' }));
  await user.click(library.getByRole('button', { name: 'Apply preset to draft' }));
  expect(await library.findByText(/The preset version changed/)).toBeVisible();
  expect(editor.getByLabelText('Main research question')).toHaveValue('Keep my draft');
  expect(screen.queryByText(/applied to the editable draft/)).not.toBeInTheDocument();
});
