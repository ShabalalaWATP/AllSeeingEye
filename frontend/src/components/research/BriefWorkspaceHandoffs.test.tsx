import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { report } from '@/test/fixtures';
import { savedMapFixture } from '@/test/fixtures.savedMaps';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import type { BriefDraft, ResearchBrief } from '@/lib/api/researchBriefSchema';
import { newBriefDraft } from '@/lib/researchBriefDraft';

const briefId = 'd73c2988-d2ca-4482-9e39-7269e876eaa0';
const mapId = '7152e032-1be9-4295-8a52-d7c63db09de4';
const mapRevision = 'd00875f8-f58c-4f6c-851d-a596925c15a9';
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

it('pins the selected older report version as metadata while copying its exact brief revision', async () => {
  const original = newBriefDraft();
  original.title = 'Historical analysis';
  original.question.main = 'What did the evidence show?';
  original.observation = {
    ...original.observation,
    policy: 'explicit',
    since: '2020-01-01T00:00:00Z',
    until: '2021-01-01T00:00:00Z',
    lookback_hours: null,
  };
  let posted: BriefDraft | null = null;
  const selected = {
    ...report,
    report: { ...report.report, latest_version: 2 },
    version: { ...report.version, number: 1, brief_id: briefId, brief_revision: 3 },
  };
  server.use(
    http.get(`/api/reports/${report.report.id}`, () => HttpResponse.json(selected)),
    http.get(`/api/research/briefs/${briefId}/revisions/3`, () =>
      HttpResponse.json({ brief: brief(original, 3) }),
    ),
    http.post('/api/research/briefs', async ({ request }) => {
      posted = (await request.json()) as BriefDraft;
      return HttpResponse.json({ brief: brief(posted) }, { status: 201 });
    }),
  );
  const { user } = renderApp(`/reports/${report.report.id}?version=1`, 'user');
  expect(await screen.findByRole('link', { name: 'Subscribe to updates' })).toHaveAttribute(
    'href',
    `/research?brief=${briefId}&revision=3&from_report=${report.report.id}&from_report_version=1&intent=subscribe`,
  );
  await user.click(await screen.findByRole('link', { name: 'Use this brief' }));
  const editor = within(await screen.findByRole('region', { name: 'Research Brief editor' }));
  expect(editor.getByLabelText('Main research question')).toHaveValue(original.question.main);
  expect(editor.getByText(/version 1/)).toBeVisible();
  await user.click(editor.getByRole('button', { name: 'Save brief' }));
  await waitFor(() => expect(posted).not.toBeNull());
  expect((posted as BriefDraft | null)?.scope).toMatchObject({
    origin_report_id: report.report.id,
    origin_version: 1,
    parent_report_id: null,
    parent_version: null,
  });
  expect((posted as BriefDraft | null)?.observation).toMatchObject(original.observation);
});

it('pins an authorised saved polygon by exact map revision without fabricating geometry', async () => {
  const map = {
    ...savedMapFixture,
    view: { ...savedMapFixture.view, id: mapId, latest_revision_id: mapRevision },
    revision: { ...savedMapFixture.revision, id: mapRevision, view_id: mapId },
  };
  let posted: BriefDraft | null = null;
  server.use(
    http.get(`/api/map/views/${mapId}/revisions/${mapRevision}`, () => HttpResponse.json(map)),
    http.post('/api/research/briefs', async ({ request }) => {
      posted = (await request.json()) as BriefDraft;
      return HttpResponse.json({ brief: brief(posted) }, { status: 201 });
    }),
  );
  const { user } = renderApp(
    `/research?brief=new&map_view=${mapId}&map_revision=${mapRevision}&question=What+changed+here%3F`,
    'user',
  );
  const editor = within(await screen.findByRole('region', { name: 'Research Brief editor' }));
  expect(editor.getByText(/From saved map/)).toBeVisible();
  expect(editor.getByLabelText('Main research question')).toHaveValue('What changed here?');
  await user.click(editor.getByRole('button', { name: 'Save brief' }));
  await waitFor(() => expect(posted).not.toBeNull());
  expect((posted as BriefDraft | null)?.scope).toMatchObject({
    map_view_id: mapId,
    map_revision_id: mapRevision,
    area: null,
    map_origin: null,
  });
  expect(map.revision.state.aoi).toEqual(savedMapFixture.revision.state.aoi);
});

it('rejects a report handoff that does not match the edition’s frozen brief revision', async () => {
  const selected = {
    ...report,
    version: { ...report.version, number: 1, brief_id: briefId, brief_revision: 2 },
  };
  server.use(http.get(`/api/reports/${report.report.id}`, () => HttpResponse.json(selected)));
  renderApp(
    `/research?brief=${briefId}&revision=3&from_report=${report.report.id}&from_report_version=1`,
    'user',
  );
  expect(
    await screen.findByText('This report edition has a different frozen brief.'),
  ).toBeVisible();
  expect(screen.queryByRole('region', { name: 'Research Brief editor' })).not.toBeInTheDocument();
});
