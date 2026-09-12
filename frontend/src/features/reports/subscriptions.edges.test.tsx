import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { aoi, schedule } from '@/test/fixtures';
import { rectangleArea } from '@/lib/map/areaGeometry';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

async function newForm() {
  const { user } = renderApp('/subscriptions', 'user');
  const form = within(await screen.findByRole('form', { name: 'New subscription' }));
  await user.type(form.getByLabelText('Subscription name'), 'Situation update');
  await user.type(form.getByLabelText('Question'), 'What changed recently?');
  return { user, form };
}

it('recovers optional topic choices after a catalogue failure and explains missing saved areas', async () => {
  server.use(
    http.get('/api/direction/aois', () =>
      HttpResponse.json(
        { error: { code: 'server_error', message: 'Area catalogue unavailable' } },
        { status: 500 },
      ),
    ),
  );
  const { user, form } = await newForm();
  await user.click(form.getByRole('button', { name: 'Choose a conflict, disaster or saved area' }));
  expect(await form.findByText('Area catalogue unavailable')).toBeVisible();
  expect(form.getByRole('button', { name: 'Create subscription' })).toBeEnabled();
  server.use(http.get('/api/direction/aois', () => HttpResponse.json({ items: [] })));
  await user.click(form.getByRole('button', { name: 'Retry choices' }));
  expect(await form.findByText(/Create an area in Plans & areas/)).toBeVisible();
  await user.click(form.getByRole('button', { name: 'Hide topic and area filters' }));
  expect(form.queryByLabelText('Saved area')).not.toBeInTheDocument();
});

it('copies a country area into the actual saved country filters and can change it to a disaster topic', async () => {
  let captured: unknown;
  server.use(
    http.get('/api/direction/aois', () =>
      HttpResponse.json({
        items: [{ ...aoi, kind: 'countries', bbox: null, countries: ['UA', 'GB'] }],
      }),
    ),
    http.post('/api/schedules', async ({ request }) => {
      captured = await request.json();
      return HttpResponse.json(schedule, { status: 201 });
    }),
  );
  const { user, form } = await newForm();
  await user.click(form.getByRole('button', { name: 'Choose a conflict, disaster or saved area' }));
  await user.selectOptions(await form.findByLabelText('Saved area'), aoi.id);
  expect(form.queryByRole('checkbox', { name: /^Allow source providers/ })).not.toBeInTheDocument();
  await user.selectOptions(form.getByLabelText('Saved area'), '');
  await user.selectOptions(form.getByLabelText('Natural disaster'), 'earthquake');
  await user.click(form.getByRole('button', { name: 'Create subscription' }));
  await waitFor(() =>
    expect(captured).toMatchObject({
      country_isos: ['UA', 'GB'],
      hazard: 'earthquake',
      conflict_id: null,
      research_area: null,
    }),
  );
});

it('preserves an exact area in a paused draft without demanding activation consent or leaking its hash', async () => {
  const geometry = { ...rectangleArea({ west: 0, south: 50, east: 1, north: 51 }) };
  const current = {
    ...schedule,
    enabled: false,
    template_id: 'ask',
    question: 'Watch this area',
    research_mode: 'quick',
    country_iso: null,
    country_isos: [],
    research_area: { geometry, sha256: 'a'.repeat(64) },
    disclose_area_to_provider: false,
    window_hours: null,
  };
  let captured: Record<string, unknown> | undefined;
  server.use(
    http.get('/api/schedules', () => HttpResponse.json({ items: [current] })),
    http.put('/api/schedules/:id', async ({ request }) => {
      captured = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json(current);
    }),
  );
  const { user } = renderApp('/subscriptions', 'user');
  const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
  await user.click(table.getByText('Saved question'));
  expect(table.getByText('Fixed area boundary')).toBeVisible();
  expect(table.getByText(/Search period matches update frequency/)).toBeVisible();
  await user.click(table.getByRole('button', { name: 'Edit' }));
  const form = within(await screen.findByRole('form', { name: 'Edit subscription' }));
  await user.click(form.getByRole('button', { name: 'Choose a conflict, disaster or saved area' }));
  expect(await form.findByRole('checkbox', { name: /^Allow source providers/ })).not.toBeChecked();
  expect(form.getByRole('button', { name: 'Save changes' })).toBeEnabled();
  await user.click(form.getByRole('button', { name: 'Save changes' }));
  await waitFor(() =>
    expect(captured).toMatchObject({
      enabled: false,
      research_area: { geometry },
      disclose_area_to_provider: false,
      window_hours: null,
    }),
  );
  expect(captured?.research_area).not.toHaveProperty('sha256');
});

it.each([
  [
    'conflict_id',
    'old-conflict',
    'Conflict',
    'Saved conflict: old-conflict',
    'quarterly',
    'day 1 every 3 months, from January at 06:00 UTC',
  ],
  [
    'hazard',
    'old-hazard',
    'Natural disaster',
    'Saved disaster: old-hazard',
    'semiannual',
    'day 1 every 6 months, from January at 06:00 UTC',
  ],
] as const)(
  'retains a saved %s when it is absent from the current catalogue',
  async (key, value, label, option, cadence, timing) => {
    const current = {
      ...schedule,
      template_id: 'ask',
      question: 'What changed?',
      research_mode: 'quick',
      [key]: value,
      cadence,
      window_hours: 6,
      country_isos: [],
    };
    server.use(http.get('/api/schedules', () => HttpResponse.json({ items: [current] })));
    const { user } = renderApp('/subscriptions', 'user');
    const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
    expect(table.getByText(timing)).toBeVisible();
    await user.click(table.getByText('Saved question'));
    expect(
      table.getByText(key === 'conflict_id' ? `Conflict: ${value}` : `Disaster: ${value}`),
    ).toBeVisible();
    expect(table.getByText(/6 hours of lookback/)).toBeVisible();
    await user.click(table.getByRole('button', { name: 'Edit' }));
    const form = within(await screen.findByRole('form', { name: 'Edit subscription' }));
    await user.click(
      form.getByRole('button', { name: 'Choose a conflict, disaster or saved area' }),
    );
    const select = await form.findByLabelText(label);
    expect(select).toHaveValue(value);
    expect(within(select).getByRole('option', { name: option })).toBeInTheDocument();
  },
);

it('converts a search period between hours and days and lets matching frequency restore its default', async () => {
  const { user, form } = await newForm();
  await user.selectOptions(form.getByLabelText('Search period'), 'hours');
  expect(form.getByLabelText('Look back, hours')).toHaveValue(168);
  await user.clear(form.getByLabelText('Look back, hours'));
  await user.type(form.getByLabelText('Look back, hours'), '25');
  await user.selectOptions(form.getByLabelText('Search period'), 'days');
  expect(form.getByLabelText('Look back, days')).toHaveValue(2);
  await user.selectOptions(form.getByLabelText('Search period'), 'default');
  expect(form.queryByLabelText('Look back, days')).not.toBeInTheDocument();
  await user.selectOptions(form.getByLabelText('Search period'), 'hours');
  expect(form.getByLabelText('Look back, hours')).toHaveValue(168);
  await user.selectOptions(form.getByLabelText('Search period'), 'default');
  await user.selectOptions(form.getByLabelText('Search period'), 'days');
  expect(form.getByLabelText('Look back, days')).toHaveValue(7);
});

it('keeps legacy weekday timing available when editing an existing live-evidence subscription', async () => {
  server.use(
    http.get('/api/schedules', () =>
      HttpResponse.json({
        items: [
          { ...schedule, template_id: 'ask', question: 'What happened?', cadence: 'weekdays' },
        ],
      }),
    ),
  );
  const { user } = renderApp('/subscriptions', 'user');
  const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
  await user.click(table.getByText('Saved question'));
  expect(table.getByText('Existing live evidence')).toBeVisible();
  await user.click(table.getByRole('button', { name: 'Edit' }));
  const form = within(await screen.findByRole('form', { name: 'Edit subscription' }));
  expect(form.getByLabelText('Cadence')).toHaveValue('weekdays');
  expect(form.getByRole('option', { name: 'Weekdays (existing)' })).toBeInTheDocument();
});
