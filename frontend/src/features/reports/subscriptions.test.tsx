import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { aoi, schedule, conflictCard } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

it.each([
  ['quarterly', 92],
  ['semiannual', 184],
  ['annual', 366],
] as const)(
  'creates a %s subscription with a matching default search window and chosen starting month',
  async (cadence, days) => {
    let captured: unknown;
    server.use(
      http.post('/api/schedules', async ({ request }) => {
        captured = await request.json();
        return HttpResponse.json(schedule, { status: 201 });
      }),
    );
    const { user } = renderApp('/subscriptions', 'user');
    const form = within(await screen.findByRole('form', { name: 'New subscription' }));
    await user.type(form.getByLabelText('Subscription name'), 'Energy outlook');
    await user.type(form.getByLabelText('Question'), 'What changed in global energy security?');
    await user.selectOptions(form.getByLabelText('Cadence'), cadence);
    expect(form.getByLabelText('Look back, days')).toHaveValue(days);
    await user.selectOptions(form.getByLabelText('Starting month'), '4');
    await user.clear(form.getByLabelText('Day of month'));
    await user.type(form.getByLabelText('Day of month'), '30');
    expect(form.getByRole('checkbox', { name: /^Prioritise new/ })).toBeChecked();
    await user.click(form.getByRole('button', { name: 'Create subscription' }));
    await waitFor(() =>
      expect(captured).toMatchObject({
        cadence,
        anchor_month: 4,
        monthday: 30,
        window_hours: days * 24,
        avoid_repetition: true,
      }),
    );
  },
);

it('uses saved area geometry and explicit provider consent while clearing other geographic filters', async () => {
  let captured: unknown;
  server.use(
    http.post('/api/schedules', async ({ request }) => {
      captured = await request.json();
      return HttpResponse.json(schedule, { status: 201 });
    }),
  );
  const { user } = renderApp('/subscriptions', 'user');
  const form = within(await screen.findByRole('form', { name: 'New subscription' }));
  await user.type(form.getByLabelText('Subscription name'), 'Regional update');
  await user.type(form.getByLabelText('Question'), 'What has changed in this area?');
  await user.click(form.getByRole('button', { name: 'Choose a conflict, disaster or saved area' }));
  await user.selectOptions(await form.findByLabelText('Conflict'), conflictCard.conflict.id);
  await user.selectOptions(form.getByLabelText('Saved area'), aoi.id);
  expect(form.getByLabelText('Conflict')).toHaveValue('');
  expect(form.getByRole('group', { name: 'Countries' })).toBeDisabled();
  const consent = form.getByRole('checkbox', { name: /^Allow source providers/ });
  expect(consent).not.toBeChecked();
  await user.click(form.getByRole('button', { name: 'Create subscription' }));
  expect(form.getByText(/Area disclosure: Allow providers/)).toBeVisible();
  expect(captured).toBeUndefined();
  await user.click(consent);
  await user.click(form.getByRole('button', { name: 'Create subscription' }));
  await waitFor(() =>
    expect(captured).toMatchObject({
      conflict_id: null,
      country_isos: [],
      disclose_area_to_provider: true,
      research_area: {
        geometry: {
          type: 'FeatureCollection',
          features: [
            {
              geometry: {
                type: 'Polygon',
                coordinates: [
                  [
                    [30, 44],
                    [41, 44],
                    [41, 53],
                    [30, 53],
                    [30, 44],
                  ],
                ],
              },
            },
          ],
        },
      },
    }),
  );
});

it('shows unchanged editions and keeps latest and previous updates accessible', async () => {
  const previous = '77777777-7777-4777-8777-777777777777';
  server.use(
    http.get('/api/schedules', () =>
      HttpResponse.json({
        items: [
          {
            ...schedule,
            cadence: 'annual',
            anchor_month: 4,
            monthday: 30,
            last_change_summary: 'No new supported development.',
            last_change: {
              status: 'unchanged',
              report_id: schedule.last_report_id,
              version_id: previous,
              previous_report_id: previous,
              previous_version_id: previous,
              baseline_version_id: previous,
              added: 0,
              removed: 0,
              updated: 0,
              reasons: [],
            },
          },
        ],
      }),
    ),
  );
  renderApp('/subscriptions', 'user');
  const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
  expect(table.getByText('No material change identified in the latest comparison.')).toBeVisible();
  expect(table.getByText('day 30 every year, from April at 06:00 UTC')).toBeVisible();
  expect(table.getByRole('link', { name: 'Previous update' })).toHaveAttribute(
    'href',
    `/reports/${previous}`,
  );
  expect(table.getByRole('link', { name: 'Latest update' })).toHaveAttribute(
    'href',
    `/reports/${schedule.last_report_id}`,
  );
});

it('preserves a custom search window when changing cadence and lets a user include repeated context', async () => {
  let captured: unknown;
  server.use(
    http.post('/api/schedules', async ({ request }) => {
      captured = await request.json();
      return HttpResponse.json(schedule, { status: 201 });
    }),
  );
  const { user } = renderApp('/subscriptions', 'user');
  const form = within(await screen.findByRole('form', { name: 'New subscription' }));
  await user.type(form.getByLabelText('Subscription name'), 'Long view');
  await user.type(form.getByLabelText('Question'), 'What is the overall position?');
  await user.clear(form.getByLabelText('Look back, days'));
  await user.type(form.getByLabelText('Look back, days'), '500');
  await user.selectOptions(form.getByLabelText('Cadence'), 'annual');
  expect(form.getByLabelText('Look back, days')).toHaveValue(500);
  await user.click(form.getByRole('checkbox', { name: /^Prioritise new/ }));
  await user.click(form.getByRole('button', { name: 'Create subscription' }));
  await waitFor(() =>
    expect(captured).toMatchObject({ window_hours: 12000, avoid_repetition: false }),
  );
});
