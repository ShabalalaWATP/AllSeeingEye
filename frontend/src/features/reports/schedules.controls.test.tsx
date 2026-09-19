import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { formatUtc } from '@/lib/format';
import { schedule } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

it('edits report depth and timing, preserves sources and paused status, then shows the next run after resume', async () => {
  let current = {
    ...schedule,
    template_id: 'ask',
    enabled: false,
    question: 'What changed at the port?',
    research_mode: 'detailed',
    research_languages: ['en', 'uk'],
    research_focus: 'general',
    research_source_ids: ['public-news'],
    research_web_search: true,
    cadence: 'monthly',
    monthday: 31,
    country_isos: ['UA', 'GB'],
    country_iso: null,
  };
  const updates: Record<string, unknown>[] = [];
  let resumeCalls = 0;
  server.use(
    http.get('/api/schedules', () => HttpResponse.json({ items: [current] })),
    http.put('/api/schedules/:id', async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      updates.push(body);
      current = { ...current, ...body, next_run_at: '2026-10-31T15:00:00Z' };
      return HttpResponse.json(current);
    }),
    http.post('/api/schedules/:id/resume', () => {
      resumeCalls++;
      current = { ...current, enabled: true };
      return HttpResponse.json(current);
    }),
  );
  const { user } = renderApp('/research/recurring', 'user');
  const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
  await user.click(table.getByRole('button', { name: 'Edit' }));
  const form = within(await screen.findByRole('form', { name: 'Edit subscription' }));
  expect(form.getByLabelText('Question')).toHaveValue(current.question);
  expect(form.getByRole('radio', { name: /^Deep/ })).toBeChecked();
  await user.click(form.getByRole('radio', { name: /^Advanced/ }));
  await user.selectOptions(form.getByLabelText('Hour'), '15');
  await user.click(form.getByRole('button', { name: 'Save changes' }));
  await screen.findByText('Subscription updated.');
  expect(updates[0]).toMatchObject({
    research_mode: 'advanced',
    hour_utc: 15,
    enabled: false,
    monthday: 31,
    country_isos: ['UA', 'GB'],
    research_source_ids: ['public-news'],
    research_languages: ['en', 'uk'],
    research_web_search: true,
  });
  await user.click(table.getByRole('button', { name: 'Resume' }));
  await table.findByRole('button', { name: 'Pause' });
  expect(table.getByText(formatUtc('2026-10-31T15:00:00Z'))).toBeVisible();
  expect(resumeCalls).toBe(1);
  expect(updates).toHaveLength(1);
});

it('retains the edit on failure and lets the operator cancel without another write', async () => {
  let writes = 0;
  server.use(
    http.put('/api/schedules/:id', () => {
      writes++;
      return HttpResponse.json(
        { error: { code: 'server_error', message: 'Could not save schedule' } },
        { status: 500 },
      );
    }),
  );
  const { user } = renderApp('/research/recurring', 'user');
  const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
  await user.click(table.getByRole('button', { name: 'Edit' }));
  const form = within(await screen.findByRole('form', { name: 'Edit subscription' }));
  await user.clear(form.getByLabelText('Subscription name'));
  await user.type(form.getByLabelText('Subscription name'), 'Updated schedule');
  await user.click(form.getByRole('button', { name: 'Save changes' }));
  expect(await form.findByText('Could not save schedule')).toBeVisible();
  expect(form.getByLabelText('Subscription name')).toHaveValue('Updated schedule');
  await user.click(form.getByRole('button', { name: 'Cancel' }));
  await screen.findByRole('form', { name: 'New subscription' });
  expect(writes).toBe(1);
});

it('filters the control panel and gives an explicit empty result', async () => {
  const { user } = renderApp('/research/recurring', 'user');
  await screen.findByRole('table', { name: 'Subscriptions' });
  await user.selectOptions(screen.getByLabelText('Show subscriptions'), 'attention');
  expect(screen.getByText('No subscriptions match these filters.')).toBeVisible();
  await user.selectOptions(screen.getByLabelText('Show subscriptions'), 'active');
  expect(screen.getByText('Morning INTSUM')).toBeVisible();
});

it('filters subscriptions by question or topic together with update frequency', async () => {
  server.use(
    http.get('/api/schedules', () =>
      HttpResponse.json({
        items: [
          {
            ...schedule,
            name: 'Baltic energy',
            question: 'How is power supply changing?',
            cadence: 'monthly',
          },
          {
            ...schedule,
            id: '29f2ac45-7912-4b23-b8c0-15c5eef784af',
            name: 'Pacific security',
            question: 'What changed around the port?',
            research_subject: 'Maritime activity',
            cadence: 'weekly',
          },
        ],
      }),
    ),
  );
  const { user } = renderApp('/research/recurring', 'user');
  const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
  expect(table.getByText('Baltic energy')).toBeVisible();
  expect(table.getByText('Pacific security')).toBeVisible();

  await user.type(screen.getByLabelText('Search subscriptions'), 'maritime');
  expect(table.queryByText('Baltic energy')).not.toBeInTheDocument();
  expect(table.getByText('Pacific security')).toBeVisible();
  await user.selectOptions(screen.getByLabelText('Update frequency'), 'monthly');
  expect(screen.getByText('No subscriptions match these filters.')).toBeVisible();
  await user.selectOptions(screen.getByLabelText('Update frequency'), 'weekly');
  expect(table.getByText('Pacific security')).toBeVisible();
});

it('always researches at the chosen depth and searches the web only when asked', async () => {
  let captured: Record<string, unknown> | undefined;
  server.use(
    http.post('/api/schedules', async ({ request }) => {
      captured = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json(schedule, { status: 201 });
    }),
  );
  const { user } = renderApp('/research/recurring', 'user');
  const form = within(await screen.findByRole('form', { name: 'New subscription' }));
  await user.type(form.getByLabelText('Subscription name'), 'Snapshot');
  await user.type(form.getByLabelText('Question'), 'What is happening?');
  // There is no "existing evidence only" switch any more: every run reads the live
  // evidence, and the depth radios stay live.
  expect(form.queryByRole('checkbox', { name: /existing live evidence/ })).toBeNull();
  expect(form.getByRole('radio', { name: /^Basic/ })).toBeEnabled();
  const web = form.getByRole('checkbox', { name: /^Also search the web each run/ });
  expect(web).not.toBeChecked();
  await user.click(form.getByRole('button', { name: 'Create subscription' }));
  await waitFor(() =>
    expect(captured).toMatchObject({ research_web_search: false, research_mode: 'quick' }),
  );
});
it('keeps the latest successful report accessible when a later scheduled run fails', async () => {
  server.use(
    http.get('/api/schedules', () =>
      HttpResponse.json({
        items: [{ ...schedule, last_error: 'The latest collection could not complete.' }],
      }),
    ),
  );
  renderApp('/research/recurring', 'user');
  const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
  expect(table.getByText('The latest collection could not complete.')).toBeVisible();
  expect(table.getByRole('link', { name: 'Last successful update' })).toHaveAttribute(
    'href',
    `/reports/${schedule.last_report_id ?? ''}`,
  );
});

it.each([6, null])(
  'preserves an existing %s-hour search period during a name-only edit',
  async (windowHours) => {
    let captured: Record<string, unknown> | undefined;
    server.use(
      http.get('/api/schedules', () =>
        HttpResponse.json({ items: [{ ...schedule, window_hours: windowHours }] }),
      ),
      http.put('/api/schedules/:id', async ({ request }) => {
        captured = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ ...schedule, ...captured });
      }),
    );
    const { user } = renderApp('/research/recurring', 'user');
    const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
    await user.click(table.getByRole('button', { name: 'Edit' }));
    const form = within(await screen.findByRole('form', { name: 'Edit subscription' }));
    if (windowHours === null) {
      expect(form.getByLabelText('Search period')).toHaveValue('default');
      expect(form.queryByLabelText('Look back, days')).not.toBeInTheDocument();
    } else expect(form.getByLabelText('Look back, hours')).toHaveValue(6);
    await user.type(form.getByLabelText('Subscription name'), ' revised');
    await user.click(form.getByRole('button', { name: 'Save changes' }));
    await waitFor(() => expect(captured).toHaveProperty('window_hours', windowHours));
  },
);

it('clears a hidden subject from general research and source preview after changing focus', async () => {
  let captured: Record<string, unknown> | undefined;
  let preview: Record<string, unknown> | undefined;
  const current = {
    ...schedule,
    template_id: 'ask',
    research_mode: 'quick',
    question: 'What changed?',
    research_focus: 'company',
    research_subject: 'Example Corporation',
  };
  server.use(
    http.get('/api/schedules', () => HttpResponse.json({ items: [current] })),
    http.put('/api/schedules/:id', async ({ request }) => {
      captured = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json({ ...current, ...captured });
    }),
    http.post('/api/research/runs/plan', async ({ request }) => {
      preview = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json({
        ...preview,
        country_iso: null,
        country_isos: [],
        request_limit: 8,
        seconds_limit: 20,
        item_limit: 50,
        policy_version: 'test',
        model_calls: 0,
        translation_calls: 0,
        replans: 0,
        tasks: [],
      });
    }),
  );
  const { user } = renderApp('/research/recurring', 'user');
  const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
  await user.click(table.getByRole('button', { name: 'Edit' }));
  const form = within(await screen.findByRole('form', { name: 'Edit subscription' }));
  await user.click(form.getByText('Advanced scope and sources'));
  await user.selectOptions(form.getByLabelText('Research focus'), 'general');
  expect(form.queryByLabelText('Research subject')).not.toBeInTheDocument();
  await user.click(form.getByRole('button', { name: 'Choose research sources' }));
  await waitFor(() => expect(preview).toMatchObject({ focus: 'general', subject: null }));
  await user.click(form.getByRole('button', { name: 'Save changes' }));
  await waitFor(() =>
    expect(captured).toMatchObject({ research_focus: 'general', research_subject: null }),
  );
});

it('prevents edit saves while a pause request is running and preserves its result', async () => {
  let current = { ...schedule };
  const writes: Record<string, unknown>[] = [];
  let release: (() => void) | undefined;
  const pending = new Promise<void>((resolve) => {
    release = resolve;
  });
  server.use(
    http.get('/api/schedules', () => HttpResponse.json({ items: [current] })),
    http.put('/api/schedules/:id', async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      writes.push(body);
      current = { ...current, ...body };
      return HttpResponse.json(current);
    }),
    http.post('/api/schedules/:id/pause', async () => {
      await pending;
      current = { ...current, enabled: false };
      return HttpResponse.json(current);
    }),
  );
  const { user } = renderApp('/research/recurring', 'user');
  const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
  await user.click(table.getByRole('button', { name: 'Edit' }));
  const form = within(await screen.findByRole('form', { name: 'Edit subscription' }));
  await user.click(table.getByRole('button', { name: 'Pause' }));
  await waitFor(() => expect(table.getByRole('button', { name: 'Pause' })).toBeDisabled());
  expect(form.getByRole('button', { name: 'Save changes' })).toBeDisabled();
  expect(table.getByRole('button', { name: 'Archive' })).toBeDisabled();
  release?.();
  await table.findByRole('button', { name: 'Resume' });
  await waitFor(() => expect(form.getByRole('button', { name: 'Save changes' })).toBeEnabled());
  await user.click(form.getByRole('button', { name: 'Save changes' }));
  await waitFor(() => expect(writes).toHaveLength(1));
  expect(writes[0]).toHaveProperty('enabled', false);
});
