import { fireEvent, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { beforeEach, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/server';
import { applySession } from '@/test/render';
import { report } from '@/test/fixtures';
import {
  areaPreview,
  consentLabel,
  mountAreaPanel,
  otherResearchArea,
  researchArea,
} from '@/test/areaResearchPanel';
import type { ResearchPlanInput } from '@/lib/api/researchPlan';
import type { ReportRequest } from '@/lib/api/reports';
import { AREA_OVERVIEW_QUESTION } from './useAreaResearch';

beforeEach(() => {
  applySession('user');
  server.use(
    http.post('/api/research/runs/plan', async ({ request }) =>
      HttpResponse.json(areaPreview((await request.json()) as ResearchPlanInput)),
    ),
  );
});
async function checkSources() {
  const button = screen.getByRole('button', { name: 'Check sources' });
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.click(button);
  await screen.findByText('1 source supports this area search');
}

it('starts without source or model calls, uses a neutral optional question and freezes the preview for generation', async () => {
  const plans: ResearchPlanInput[] = [];
  const requests: ReportRequest[] = [];
  server.use(
    http.post('/api/research/runs/plan', async ({ request }) => {
      const input = (await request.json()) as ResearchPlanInput;
      plans.push(input);
      return HttpResponse.json(areaPreview(input));
    }),
    http.post('/api/reports', async ({ request }) => {
      requests.push((await request.json()) as ReportRequest);
      return HttpResponse.json(report, { status: 201 });
    }),
  );
  const view = mountAreaPanel();
  expect(screen.getByRole('button', { name: 'Generate area report' })).toBeDisabled();
  expect(screen.getByLabelText('Research depth')).toHaveValue('detailed');
  expect(screen.getByLabelText('Research period')).toHaveValue('1');
  expect(plans).toHaveLength(0);
  expect(requests).toHaveLength(0);
  await checkSources();
  expect(plans[0]).toMatchObject({
    question: AREA_OVERVIEW_QUESTION,
    research_area: { geometry: researchArea },
    team_id: null,
    source_ids: null,
  });
  expect(Date.parse(plans[0]!.until) - Date.parse(plans[0]!.since)).toBe(86_400_000);
  expect(screen.getByRole('button', { name: 'Generate area report' })).toBeDisabled();
  fireEvent.click(screen.getByLabelText(consentLabel));
  fireEvent.click(screen.getByRole('button', { name: 'Generate area report' }));
  await waitFor(() => expect(requests).toHaveLength(1));
  expect(requests[0]).toMatchObject({
    template: 'ask',
    question: plans[0]!.question,
    research_area: plans[0]!.research_area,
    research_since: plans[0]!.since,
    research_until: plans[0]!.until,
    research_mode: 'detailed',
    devils_advocacy: true,
    research_source_ids: null,
    team_id: null,
    disclose_area_to_provider: true,
  });
  expect(requests[0]).not.toHaveProperty('map_view_id');
  expect(requests[0]).not.toHaveProperty('parent_report_id');
  expect(requests[0]).not.toHaveProperty('window_hours');
  await waitFor(() =>
    expect(screen.getByLabelText('Current location')).toHaveTextContent(
      `/reports/${report.report.id}`,
    ),
  );
  expect(view.stop).toHaveBeenCalledOnce();
});

it.each(['question', 'period', 'depth', 'boundary'] as const)(
  'invalidates source check and consent when %s changes',
  async (field) => {
    const view = mountAreaPanel();
    await checkSources();
    fireEvent.click(screen.getByLabelText(consentLabel));
    if (field === 'question')
      fireEvent.change(screen.getByLabelText('Question (optional)'), {
        target: { value: 'What changed?' },
      });
    if (field === 'period')
      fireEvent.change(screen.getByLabelText('Research period'), { target: { value: '3' } });
    if (field === 'depth')
      fireEvent.change(screen.getByLabelText('Research depth'), { target: { value: 'quick' } });
    if (field === 'boundary') view.update({ area: otherResearchArea });
    expect(screen.queryByLabelText('Area source coverage')).not.toBeInTheDocument();
    expect(screen.getByLabelText(consentLabel)).not.toBeChecked();
    expect(screen.getByRole('button', { name: 'Generate area report' })).toBeDisabled();
    await checkSources();
    expect(screen.getByLabelText(consentLabel)).not.toBeChecked();
  },
);

it('shows unsupported source reasons and prevents collection when no provider supports the area', async () => {
  server.use(
    http.post('/api/research/runs/plan', async ({ request }) =>
      HttpResponse.json(areaPreview((await request.json()) as ResearchPlanInput, false)),
    ),
  );
  mountAreaPanel();
  await waitFor(() => expect(screen.getByRole('button', { name: 'Check sources' })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: 'Check sources' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('No selected source supports');
  const user = userEvent.setup();
  await user.click(screen.getByText('Sources without area support (2)'));
  expect(screen.getByText('News archive')).toBeVisible();
  expect(screen.getByLabelText(consentLabel)).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Generate area report' })).toBeDisabled();
});

it('requires a valid completed boundary and permits retry after preview failure', async () => {
  const view = mountAreaPanel({ area: null });
  expect(screen.getByRole('button', { name: 'Check sources' })).toBeDisabled();
  view.update({ areaError: 'Boundary crosses itself.' });
  expect(screen.getByRole('alert')).toHaveTextContent('Boundary crosses itself.');
  view.update({ picking: true });
  expect(screen.getByRole('button', { name: 'Check sources' })).toBeDisabled();
  server.use(
    http.post('/api/research/runs/plan', () =>
      HttpResponse.json(
        { error: { code: 'unavailable', message: 'Try later', fields: {} } },
        { status: 503 },
      ),
    ),
  );
  view.update({ area: researchArea });
  await waitFor(() => expect(screen.getByRole('button', { name: 'Check sources' })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: 'Check sources' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Try later');
  expect(screen.getByRole('button', { name: 'Check sources' })).toBeEnabled();
});

it('rejects a source preview for a different area', async () => {
  server.use(
    http.post('/api/research/runs/plan', async ({ request }) => {
      const response = areaPreview((await request.json()) as ResearchPlanInput);
      return HttpResponse.json({
        ...response,
        area: { ...response.area, geometry: otherResearchArea },
      });
    }),
  );
  mountAreaPanel();
  await waitFor(() => expect(screen.getByRole('button', { name: 'Check sources' })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: 'Check sources' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('does not match this area');
  expect(screen.getByRole('button', { name: 'Generate area report' })).toBeDisabled();
});

it.each([
  'question',
  'since',
  'until',
  'mode',
  'focus',
  'languages',
  'time_basis',
  'area',
] as const)('rejects a source preview with a changed %s', async (field) => {
  server.use(
    http.post('/api/research/runs/plan', async ({ request }) => {
      const response = areaPreview((await request.json()) as ResearchPlanInput);
      const changes: Record<string, unknown> = {
        question: 'Different question',
        since: '2020-01-01T00:00:00Z',
        until: '2020-01-02T00:00:00Z',
        mode: 'quick',
        focus: 'company',
        languages: ['fr'],
        time_basis: 'publication',
        area: null,
      };
      return HttpResponse.json({ ...response, [field]: changes[field] });
    }),
  );
  mountAreaPanel();
  await waitFor(() => expect(screen.getByRole('button', { name: 'Check sources' })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: 'Check sources' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('does not match this area');
  expect(screen.getByRole('button', { name: 'Generate area report' })).toBeDisabled();
});

it('reports model failures without losing the checked area or enabling duplicate requests', async () => {
  server.use(
    http.post('/api/reports', () =>
      HttpResponse.json(
        { error: { code: 'unavailable', message: 'AI connection unavailable.', fields: {} } },
        { status: 503 },
      ),
    ),
  );
  mountAreaPanel();
  await checkSources();
  fireEvent.click(screen.getByLabelText(consentLabel));
  fireEvent.click(screen.getByRole('button', { name: 'Generate area report' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('AI connection unavailable.');
  expect(screen.getByLabelText('Area source coverage')).toBeVisible();
  expect(screen.getByRole('button', { name: 'Generate area report' })).toBeEnabled();
});
