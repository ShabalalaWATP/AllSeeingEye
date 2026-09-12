import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { alert, schedule } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

it('saves an explicit question and bounded research options for each scheduled run', async () => {
  let captured: unknown;
  server.use(
    http.post('/api/schedules', async ({ request }) => {
      captured = await request.json();
      return HttpResponse.json(schedule, { status: 201 });
    }),
  );
  const { user } = renderApp('/research/recurring', 'user');
  const form = within(await screen.findByRole('form', { name: 'New schedule' }));
  await user.click(form.getByText('Advanced scope and sources'));
  await user.type(form.getByLabelText('Schedule name'), 'Weekly port research');
  await user.selectOptions(form.getByLabelText('Product'), 'ask');
  expect(form.getByRole('button', { name: 'Add schedule' })).toBeDisabled();
  await user.type(form.getByLabelText('Question'), 'What changed at the port?');
  expect(
    form.getByRole('checkbox', { name: /^Notify in app when evidence changes/ }),
  ).toBeChecked();
  await user.click(form.getByRole('radio', { name: /^Deep/ }));
  await user.clear(form.getByLabelText('Research languages'));
  await user.type(form.getByLabelText('Research languages'), 'en; bad');
  expect(form.getByRole('button', { name: 'Add schedule' })).toBeDisabled();
  await user.clear(form.getByLabelText('Research languages'));
  await user.type(form.getByLabelText('Research languages'), 'en, uk, en');
  await user.click(form.getByText('Choose countries'));
  await user.click(form.getByRole('checkbox', { name: /^Ukraine/ }));
  await user.selectOptions(form.getByLabelText('Research focus'), 'company');
  expect(form.getByRole('group', { name: 'Countries' })).toBeDisabled();
  expect(form.getByRole('button', { name: 'Add schedule' })).toBeDisabled();
  expect(form.getByLabelText('Research subject')).toBeRequired();
  await user.type(form.getByLabelText('Research subject'), 'Example Port');
  await user.click(form.getByRole('button', { name: 'Add schedule' }));
  await waitFor(() =>
    expect(captured).toMatchObject({
      notify_on_change: true,
      country_iso: null,
      template_id: 'ask',
      question: 'What changed at the port?',
      research_mode: 'detailed',
      research_languages: ['en', 'uk'],
      research_focus: 'company',
      research_subject: 'Example Port',
    }),
  );
});

it('does not submit stale research fields after switching to an ordinary product', async () => {
  let captured: unknown;
  server.use(
    http.post('/api/schedules', async ({ request }) => {
      captured = await request.json();
      return HttpResponse.json(schedule, { status: 201 });
    }),
  );
  const { user } = renderApp('/research/recurring', 'user');
  const form = within(await screen.findByRole('form', { name: 'New schedule' }));
  await user.click(form.getByText('Advanced scope and sources'));
  await user.type(form.getByLabelText('Schedule name'), 'Daily overview');
  await user.selectOptions(form.getByLabelText('Product'), 'ask');
  await user.type(form.getByLabelText('Question'), 'Old question');
  await user.click(form.getByRole('radio', { name: /^Basic/ }));
  await user.selectOptions(form.getByLabelText('Product'), 'intsum');
  await user.click(form.getByRole('button', { name: 'Add schedule' }));
  await waitFor(() => expect(captured).toMatchObject({ template_id: 'intsum' }));
  expect(captured).not.toHaveProperty('question');
  expect(captured).not.toHaveProperty('research_mode');
});

it('shows the saved question and research settings beside its standing order', async () => {
  server.use(
    http.get('/api/schedules', () =>
      HttpResponse.json({
        items: [
          {
            ...schedule,
            question: 'What changed at the port?',
            research_mode: 'detailed',
            research_languages: ['en', 'uk'],
            research_focus: 'company',
            research_subject: 'Example Port',
          },
        ],
      }),
    ),
  );
  const { user } = renderApp('/research/recurring', 'user');
  const table = within(await screen.findByRole('table', { name: 'Schedules' }));
  await user.click(table.getByText('Saved question'));
  expect(table.getByText('What changed at the port?')).toBeVisible();
  expect(table.getByText('Deep research, en, uk, company')).toBeVisible();
  expect(table.getByText('Example Port')).toBeVisible();
});

it('shows the baseline summary without inventing an alert', async () => {
  server.use(
    http.get('/api/schedules', () =>
      HttpResponse.json({
        items: [
          {
            ...schedule,
            notify_on_change: true,
            last_change_summary:
              'Baseline established. Future runs compare frozen evidence and assessments.',
          },
        ],
      }),
    ),
  );
  renderApp('/research/recurring', 'user');
  expect(
    await screen.findByText(
      'Baseline established. Future runs compare frozen evidence and assessments.',
    ),
  ).toBeVisible();
});

it('shows a schedule-origin alert through the existing warning view', async () => {
  server.use(
    http.get('/api/warning/alerts', () =>
      HttpResponse.json({
        unacknowledged: 1,
        items: [
          {
            ...alert,
            indicator_id: null,
            schedule_id: schedule.id,
            title: 'Evidence changed: Weekly port question',
            summary:
              'Evidence: 1 added, 0 removed, 0 changed. Factual accuracy is not established.',
          },
        ],
      }),
    ),
  );
  renderApp('/warning', 'user');
  expect(await screen.findByText('Evidence changed: Weekly port question')).toBeVisible();
  expect(
    screen.getByText(
      'Evidence: 1 added, 0 removed, 0 changed. Factual accuracy is not established.',
    ),
  ).toBeVisible();
});
