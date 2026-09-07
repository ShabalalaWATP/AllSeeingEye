import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { report } from '@/test/fixtures';
import { savedMapFixture } from '@/test/fixtures.savedMaps';
import { applySession, renderApp } from '@/test/render';
import { server } from '@/test/server';
import type { ResearchPlanInput } from '@/lib/api/researchPlan';
import type { ReportRequest } from '@/lib/api/reports';

const viewId = '00000000-0000-4000-8000-000000000001';
const revisionId = '00000000-0000-4000-8000-000000000002';
const saved = {
  ...savedMapFixture,
  view: { ...savedMapFixture.view, id: viewId },
  revision: { ...savedMapFixture.revision, id: revisionId, view_id: viewId },
};
const path = `/research?map_view=${viewId}&map_revision=${revisionId}`;

it('launches historical project research from the exact saved area and resets consent on year edits', async () => {
  let submitted: ReportRequest | undefined;
  server.use(
    http.get('/api/map/views/:view/revisions/:revision', () => HttpResponse.json(saved)),
    http.post('/api/research/runs/plan', async ({ request }) =>
      HttpResponse.json(preview((await request.json()) as ResearchPlanInput)),
    ),
    http.post('/api/reports', async ({ request }) => {
      submitted = (await request.json()) as ReportRequest;
      return HttpResponse.json(report, { status: 201 });
    }),
  );
  const { user } = renderApp(path, 'user');
  await user.type(await screen.findByLabelText('Your area research question'), 'Which projects?');
  await user.selectOptions(screen.getByLabelText('Research period'), 'history');
  await user.type(screen.getByLabelText('Project ID (optional)'), '35756');
  await user.click(screen.getByText('Collection plan (required)'));
  await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
  await screen.findByText('Current preview');
  const consent = screen.getByLabelText(
    'Allow selected providers to receive this area and interval for collection.',
  );
  for (const identifier of ['100', '', '35756']) {
    await user.click(consent);
    fireEvent.change(screen.getByLabelText('Project ID (optional)'), {
      target: { value: identifier },
    });
    expect(consent).not.toBeChecked();
    expect(screen.queryByText('Current preview')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Research saved area' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
    await screen.findByText('Current preview');
  }
  await user.click(consent);
  await user.clear(screen.getByLabelText('Last commitment year'));
  await user.type(screen.getByLabelText('Last commitment year'), '2020');
  expect(consent).not.toBeChecked();
  expect(screen.getByRole('button', { name: 'Research saved area' })).toBeDisabled();
  await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
  await screen.findByText('Current preview');
  await user.click(consent);
  await user.click(screen.getByRole('button', { name: 'Research saved area' }));
  await waitFor(() =>
    expect(submitted).toMatchObject({
      map_view_id: viewId,
      map_revision_id: revisionId,
      research_source_ids: ['research-aiddata-projects'],
      research_terms: ['aiddata:35756'],
      research_time_basis: 'recorded_time',
      research_since: '2000-01-01T00:00:00.000Z',
      research_until: '2021-01-01T00:00:00.000Z',
    }),
  );
  expect(submitted?.window_hours).toBeUndefined();
});
function preview(input: ResearchPlanInput) {
  return {
    ...input,
    subject: null,
    country_iso: null,
    languages: ['en'],
    area: { geometry: saved.revision.state.aoi!, sha256: 'a'.repeat(64) },
    request_limit: 6,
    seconds_limit: 45,
    item_limit: 200,
    policy_version: 'fixture',
    model_calls: 0,
    translation_calls: 0,
    replans: 0,
    map_origin: {
      view_id: viewId,
      revision_id: revisionId,
      report_id: viewId,
      report_version_id: revisionId,
      report_version_number: 1,
      content_sha256: 'b'.repeat(64),
      evidence_sha256: 'c'.repeat(64),
      area: { geometry: saved.revision.state.aoi!, sha256: 'a'.repeat(64) },
    },
    tasks: [
      {
        source_id:
          input.time_basis === 'recorded_time'
            ? 'research-aiddata-projects'
            : 'research-copernicus-footprints',
        source_name: 'Copernicus',
        selected: true,
        supported: true,
        spatial_supported: true,
        spatial_scope: 'Rectangle',
        language: null,
        terms: [],
        provenance: 'original_terms',
        temporal_scope: 'requested_window',
      },
    ],
  };
}

it('requires a current exact-area preview and submits its fixed dates without a parent or rolling scope', async () => {
  const plans: ResearchPlanInput[] = [];
  let submitted: ReportRequest | undefined;
  server.use(
    http.get('/api/map/views/:view/revisions/:revision', () => HttpResponse.json(saved)),
    http.post('/api/research/runs/plan', async ({ request }) => {
      const input = (await request.json()) as ResearchPlanInput;
      plans.push(input);
      return HttpResponse.json(preview(input));
    }),
    http.post('/api/reports', async ({ request }) => {
      submitted = (await request.json()) as ReportRequest;
      return HttpResponse.json(report, { status: 201 });
    }),
  );
  const { user } = renderApp(path, 'user');
  await user.type(
    await screen.findByLabelText('Your area research question'),
    'What was observed?',
  );
  expect(screen.queryByLabelText('Your question')).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Acquisition / publication from (UTC)'), {
    target: { value: '2020-01-01T10:00' },
  });
  fireEvent.change(screen.getByLabelText('Acquisition / publication until (UTC, exclusive)'), {
    target: { value: '2020-01-01T12:00' },
  });
  await user.click(screen.getByText('Collection plan (required)'));
  await user.click(screen.getByRole('button', { name: /Preview collection plan/ }));
  await screen.findByRole('checkbox', { name: 'Copernicus' });
  expect(screen.getByRole('button', { name: 'Research saved area' })).toBeDisabled();
  await user.click(
    screen.getByLabelText(
      'Allow selected providers to receive this area and interval for collection.',
    ),
  );
  expect(screen.getByRole('button', { name: 'Research saved area' })).toBeEnabled();
  fireEvent.change(screen.getByLabelText('Acquisition / publication until (UTC, exclusive)'), {
    target: { value: '2020-01-01T13:00' },
  });
  expect(screen.getByRole('button', { name: 'Research saved area' })).toBeDisabled();
  await user.click(screen.getByRole('button', { name: /Preview collection plan/ }));
  await waitFor(() => expect(plans).toHaveLength(2));
  await user.click(
    screen.getByLabelText(
      'Allow selected providers to receive this area and interval for collection.',
    ),
  );
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Research saved area' })).toBeEnabled(),
  );
  await user.click(screen.getByRole('button', { name: 'Research saved area' }));
  await waitFor(() => expect(submitted).toBeDefined());
  expect(submitted).toMatchObject({
    map_view_id: viewId,
    map_revision_id: revisionId,
    team_id: null,
    disclose_area_to_provider: true,
    research_focus: 'general',
  });
  expect(Date.parse(submitted!.research_since!)).toBe(Date.parse(plans[1]!.since));
  expect(Date.parse(submitted!.research_until!)).toBe(Date.parse(plans[1]!.until));
  expect(submitted).not.toHaveProperty('parent_report_id');
  expect(submitted).not.toHaveProperty('window_hours');
  expect(plans[1]).toMatchObject({
    map_view_id: viewId,
    map_revision_id: revisionId,
    team_id: null,
  });
});

it('does not fall back to ordinary research for an incomplete map link', async () => {
  renderApp(`/research?map_view=${viewId}`, 'user');
  expect(await screen.findByRole('alert')).toHaveTextContent('exact saved map revision');
  expect(screen.queryByRole('form', { name: 'Research a question' })).not.toBeInTheDocument();
});

it('aborts a pending private map load on account change', async () => {
  let started = false,
    aborted = false;
  let finish: () => void = () => undefined;
  const done = new Promise<void>((resolve) => {
    finish = resolve;
  });
  server.use(
    http.get('/api/map/views/:view/revisions/:revision', async ({ request }) => {
      started = true;
      request.signal.addEventListener('abort', () => {
        aborted = true;
      });
      await done;
      return HttpResponse.json(saved);
    }),
  );
  const page = renderApp(path, 'user');
  await waitFor(() => expect(started).toBe(true));
  act(() => applySession('anonymous'));
  await waitFor(() => expect(aborted).toBe(true));
  finish();
  expect(screen.queryByRole('form', { name: 'Research a saved area' })).not.toBeInTheDocument();
  page.unmount();
});

it('refuses another owner�s personal area and never offers to change its destination', async () => {
  server.use(
    http.get('/api/map/views/:view/revisions/:revision', () =>
      HttpResponse.json({
        ...saved,
        view: { ...saved.view, created_by: 'another-owner' },
      }),
    ),
  );
  renderApp(path, 'user');
  expect(await screen.findByText(/ownership or team permissions/)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Research saved area' })).toBeDisabled();
  expect(screen.queryByLabelText('Workspace')).not.toBeInTheDocument();
});

it.each(['revision', 'interval'])('rejects a preview with a mismatched %s', async (mismatch) => {
  server.use(
    http.get('/api/map/views/:view/revisions/:revision', () => HttpResponse.json(saved)),
    http.post('/api/research/runs/plan', async ({ request }) => {
      const result = preview((await request.json()) as ResearchPlanInput);
      if (mismatch === 'revision') result.map_origin.revision_id = viewId;
      else result.until = '2020-01-02T12:00:00Z';
      return HttpResponse.json(result);
    }),
  );
  const { user } = renderApp(path, 'user');
  await user.type(
    await screen.findByLabelText('Your area research question'),
    'What was observed?',
  );
  fireEvent.change(screen.getByLabelText('Acquisition / publication from (UTC)'), {
    target: { value: '2020-01-01T10:00' },
  });
  fireEvent.change(screen.getByLabelText('Acquisition / publication until (UTC, exclusive)'), {
    target: { value: '2020-01-01T12:00' },
  });
  await user.click(screen.getByText('Collection plan (required)'));
  await user.click(screen.getByRole('button', { name: /Preview collection plan/ }));
  expect(await screen.findByRole('alert')).toHaveTextContent('preview does not match');
  expect(screen.getByRole('button', { name: 'Research saved area' })).toBeDisabled();
});
