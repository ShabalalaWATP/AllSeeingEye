import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/server';
import { applySession } from '@/test/render';
import { areaPreview, consentLabel, mountAreaPanel, researchArea } from '@/test/areaResearchPanel';
import { liveEvent } from '@/test/fixtures.events';
import type { ResearchPlanInput } from '@/lib/api/researchPlan';
import { readAreaResearchHandoff, useAreaResearchDraft } from '@/lib/areaResearchDraft';

beforeEach(() => applySession('user'));

function trackPreviews() {
  const plans: ResearchPlanInput[] = [];
  server.use(
    http.post('/api/research/runs/plan', async ({ request }) => {
      const input = (await request.json()) as ResearchPlanInput;
      plans.push(input);
      const result = areaPreview(input);
      result.tasks.forEach((task) => {
        task.selected = input.source_ids == null || input.source_ids.includes(task.source_id);
      });
      return HttpResponse.json(result);
    }),
  );
  return plans;
}
async function check() {
  const button = screen.getByRole('button', { name: /^(Check sources|Refresh source check)$/ });
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.click(button);
  await screen.findByText('1 source supports this area search');
}

it('keeps collection capability separate from evidence and forwards selected sources only after a new preview', async () => {
  const plans = trackPreviews();
  mountAreaPanel();
  await check();
  fireEvent.click(screen.getByLabelText(consentLabel));
  fireEvent.click(screen.getByText('Sources supporting this query (1)'));
  fireEvent.click(screen.getByRole('checkbox', { name: 'NASA FIRMS' }));
  expect(screen.getByLabelText(consentLabel)).not.toBeChecked();
  expect(screen.getByRole('button', { name: 'Generate area report' })).toBeDisabled();
  expect(screen.getByText(/These sources have not been contacted/)).toBeVisible();
  fireEvent.click(screen.getByRole('checkbox', { name: 'NASA FIRMS' }));
  expect(screen.getByRole('button', { name: 'Generate area report' })).toBeDisabled();
  await check();
  expect(plans[1]?.source_ids).toEqual(['research-firms']);
  expect(screen.getByLabelText(consentLabel)).not.toBeChecked();
});

it('does not revive approval when an edited question is restored', async () => {
  trackPreviews();
  mountAreaPanel();
  await check();
  fireEvent.click(screen.getByLabelText(consentLabel));
  fireEvent.change(screen.getByLabelText('Question (optional)'), { target: { value: 'Edited' } });
  fireEvent.change(screen.getByLabelText('Question (optional)'), { target: { value: '' } });
  expect(screen.queryByLabelText('Area source coverage')).not.toBeInTheDocument();
  expect(screen.getByLabelText(consentLabel)).not.toBeChecked();
});

it('hands off exact scope, fixed time and preferences without copying consent or putting geometry in the URL', async () => {
  const plans = trackPreviews();
  mountAreaPanel();
  fireEvent.change(screen.getByLabelText('Question (optional)'), {
    target: { value: 'Harbour activity?' },
  });
  fireEvent.change(screen.getByLabelText('Research period'), { target: { value: '7' } });
  await check();
  fireEvent.click(screen.getByRole('button', { name: 'Continue on research page' }));
  expect(screen.getByLabelText('Current location')).toHaveTextContent('/research');
  expect(readAreaResearchHandoff()?.area).toEqual(researchArea);
  expect(readAreaResearchHandoff()?.preferences?.report_language).toBeDefined();
  expect(useAreaResearchDraft.getState().interval).toEqual({
    since: plans[0]?.since,
    until: plans[0]?.until,
  });
  expect(useAreaResearchDraft.getState().question).toBe('Harbour activity?');
  expect(useAreaResearchDraft.getState().days).toBe(7);
});

it('previews the loaded subset locally and links observations back to the map', () => {
  const event = liveEvent({
    point: { lon: 0.5, lat: 50.5 },
    published_at: new Date(Date.now() - 3600000).toISOString(),
  });
  const highlight = vi.fn();
  mountAreaPanel({ events: [event], onHighlight: highlight });
  const preview = screen.getByRole('region', { name: 'Retained evidence in this area' });
  expect(within(preview).getByText('1 precisely located observations inside')).toBeVisible();
  expect(within(preview).getByText(/No provider or AI is contacted/)).toBeVisible();
  fireEvent.click(within(preview).getByText('Precisely inside (1)'));
  fireEvent.click(within(preview).getByRole('button', { name: event.title }));
  expect(highlight).toHaveBeenCalledWith(event);
});
