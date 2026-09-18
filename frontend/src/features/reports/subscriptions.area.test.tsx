import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { rectangleArea } from '@/lib/map/areaGeometry';
import { schedule } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const geometry = { ...rectangleArea({ west: 30, south: 44, east: 41, north: 53 }) };

async function editBoundedSubscription(enabled: boolean) {
  const current = {
    ...schedule,
    enabled,
    template_id: 'ask',
    question: 'What changed in this area?',
    research_mode: 'quick',
    country_iso: null,
    country_isos: [],
    research_area: { geometry, sha256: 'b'.repeat(64) },
    disclose_area_to_provider: false,
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
  await user.click(table.getByRole('button', { name: 'Edit' }));
  const form = within(await screen.findByRole('form', { name: 'Edit subscription' }));
  return { user, form, read: () => captured };
}

it('shows a boundary drawn on the map, needs consent to run it, and keeps its exact shape', async () => {
  const { user, form, read } = await editBoundedSubscription(true);
  expect(form.getByText(/A boundary drawn on the map is saved/)).toBeVisible();
  // The boundary is the place, so regions, nations and the conflict pin stand down.
  expect(form.getByRole('group', { name: 'Regions' })).toBeDisabled();
  expect(form.getByRole('group', { name: 'Nations' })).toBeDisabled();
  expect(await form.findByLabelText('Conflict')).toBeDisabled();
  const consent = form.getByRole('checkbox', { name: /^Allow source providers/ });
  expect(consent).not.toBeChecked();
  await user.click(form.getByRole('button', { name: 'Save changes' }));
  expect(form.getByText(/Area disclosure: Allow providers/)).toBeVisible();
  expect(read()).toBeUndefined();
  await user.click(consent);
  await user.click(form.getByRole('button', { name: 'Save changes' }));
  await waitFor(() =>
    expect(read()).toMatchObject({
      country_isos: [],
      regions: [],
      disclose_area_to_provider: true,
      research_area: { geometry },
    }),
  );
  expect(read()?.research_area).not.toHaveProperty('sha256');
});

it('lets the boundary be cleared, which hands the place back to regions and nations', async () => {
  const { user, form, read } = await editBoundedSubscription(true);
  await user.click(form.getByRole('button', { name: 'Clear boundary' }));
  expect(form.queryByText(/A boundary drawn on the map is saved/)).toBeNull();
  expect(form.getByRole('group', { name: 'Regions' })).toBeEnabled();
  await user.click(form.getByRole('checkbox', { name: 'Europe' }));
  await user.click(form.getByRole('button', { name: 'Save changes' }));
  await waitFor(() => expect(read()).toMatchObject({ research_area: null, regions: ['europe'] }));
});

it('saves regions and themes, and holds each to its limit', async () => {
  let captured: Record<string, unknown> | undefined;
  server.use(
    http.post('/api/schedules', async ({ request }) => {
      captured = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json(schedule, { status: 201 });
    }),
  );
  const { user } = renderApp('/subscriptions', 'user');
  const form = within(await screen.findByRole('form', { name: 'New subscription' }));
  await user.type(form.getByLabelText('Subscription name'), 'Two regions, four themes');
  await user.type(form.getByLabelText('Question'), 'What is changing across the region?');
  await user.click(form.getByRole('checkbox', { name: 'Europe' }));
  await user.click(form.getByRole('checkbox', { name: 'Middle East' }));
  const themes = within(form.getByRole('group', { name: 'Themes' }));
  for (const theme of ['Cyber', 'Economy', 'Politics', 'Conflict']) {
    await user.click(themes.getByRole('checkbox', { name: theme }));
  }
  // Four is the limit: a fifth theme cannot be ticked until one is removed.
  expect(themes.getByRole('checkbox', { name: 'Disasters' })).toBeDisabled();
  expect(themes.getByRole('status')).toHaveTextContent('4 chosen. Remove one to add another.');
  await user.click(form.getByRole('button', { name: 'Create subscription' }));
  await waitFor(() =>
    expect(captured).toMatchObject({
      regions: ['europe', 'middle_east'],
      categories: ['cyber', 'economic', 'political', 'conflict'],
      country_isos: [],
    }),
  );
});
