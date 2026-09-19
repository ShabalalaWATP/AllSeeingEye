import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import type { ResearchPlanInput } from '@/lib/api/researchPlan';
import { schedule } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

it('saves monthly multi-country research with a two-year lookback, web search and source choices', async () => {
  let captured: unknown;
  let previewInput: ResearchPlanInput | undefined;
  server.use(
    http.post('/api/schedules', async ({ request }) => {
      captured = await request.json();
      return HttpResponse.json(schedule, { status: 201 });
    }),
    http.post('/api/research/runs/plan', async ({ request }) => {
      previewInput = (await request.json()) as ResearchPlanInput;
      return HttpResponse.json({
        ...previewInput,
        subject: null,
        country_iso: null,
        country_isos: previewInput.countries,
        request_limit: 8,
        seconds_limit: 20,
        item_limit: 50,
        policy_version: 'test',
        model_calls: 0,
        translation_calls: 0,
        replans: 0,
        tasks: ['Public news', 'Open archive'].map((name, i) => ({
          source_id: `source-${i}`,
          source_name: name,
          selected: true,
          supported: true,
          language: 'en',
          terms: [],
          provenance: 'public source',
          temporal_scope: 'Partial history',
        })),
      });
    }),
  );
  const { user } = renderApp('/research/recurring', 'user');
  const form = within(await screen.findByRole('form', { name: 'New subscription' }));
  await user.type(form.getByLabelText('Subscription name'), 'Monthly regional energy');
  await user.type(form.getByLabelText('Question'), 'What changed in energy policy?');
  await user.click(form.getByText('Choose countries'));
  await user.click(form.getByRole('checkbox', { name: /^Ukraine/ }));
  await user.click(form.getByRole('checkbox', { name: /^United Kingdom/ }));
  await user.selectOptions(form.getByLabelText('Cadence'), 'monthly');
  await user.clear(form.getByLabelText('Day of month'));
  await user.type(form.getByLabelText('Day of month'), '31');
  expect(form.getByText(/For short months/)).toBeVisible();
  await user.clear(form.getByLabelText('Look back, days'));
  await user.type(form.getByLabelText('Look back, days'), '731');
  await user.click(form.getByRole('button', { name: 'Create subscription' }));
  expect(form.getByText(/Search period: Choose a search period within two years/)).toBeVisible();
  await user.clear(form.getByLabelText('Look back, days'));
  await user.type(form.getByLabelText('Look back, days'), '730');
  await user.click(form.getByRole('checkbox', { name: /^Also search the web each run/ }));
  await user.click(form.getByText('Advanced scope and sources'));
  await user.click(form.getByRole('button', { name: 'Choose research sources' }));
  await user.click(await form.findByRole('checkbox', { name: /^Public news/ }));
  await user.click(form.getByRole('button', { name: 'Create subscription' }));
  await waitFor(() =>
    expect(captured).toMatchObject({
      cadence: 'monthly',
      monthday: 31,
      country_iso: null,
      country_isos: ['UA', 'GB'],
      window_hours: 17520,
      research_web_search: true,
      research_source_ids: ['source-1'],
      question: 'What changed in energy policy?',
      research_mode: 'quick',
    }),
  );
  expect(previewInput?.countries).toEqual(['UA', 'GB']);
});

it('pauses and resumes without losing saved countries, source choices or the monthly day', async () => {
  let current = {
    ...schedule,
    cadence: 'monthly',
    monthday: 31,
    country_iso: null,
    country_isos: ['UA', 'GB'],
    question: 'What changed?',
    research_mode: 'quick',
    research_web_search: true,
    research_source_ids: ['source-1'],
    window_hours: 17520,
  };
  const transitions: boolean[] = [];
  server.use(
    http.get('/api/schedules', () => HttpResponse.json({ items: [current] })),
    http.post('/api/schedules/:id/pause', () => {
      current = { ...current, enabled: false };
      transitions.push(current.enabled);
      return HttpResponse.json(current);
    }),
    http.post('/api/schedules/:id/resume', () => {
      current = { ...current, enabled: true };
      transitions.push(current.enabled);
      return HttpResponse.json(current);
    }),
  );
  const { user } = renderApp('/research/recurring', 'user');
  const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
  expect(table.getByText('day 31 each month at 06:00 UTC')).toBeVisible();
  await user.click(table.getByRole('button', { name: 'Pause' }));
  expect(await table.findByText('Paused')).toBeVisible();
  await user.click(table.getByRole('button', { name: 'Resume' }));
  await table.findByRole('button', { name: 'Pause' });
  expect(transitions).toEqual([false, true]);
  expect(current).toMatchObject({
    country_isos: ['UA', 'GB'],
    monthday: 31,
    research_web_search: true,
    research_source_ids: ['source-1'],
    window_hours: 17520,
  });
});
