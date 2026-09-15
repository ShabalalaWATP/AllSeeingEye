import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { schedule } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { newBriefDraft } from '@/lib/researchBriefDraft';

it('shows linked validation errors without submitting an incomplete subscription', async () => {
  let writes = 0;
  server.use(
    http.post('/api/schedules', () => {
      writes += 1;
      return HttpResponse.json(schedule, { status: 201 });
    }),
  );
  const { user } = renderApp('/research/recurring', 'user');
  const form = within(await screen.findByRole('form', { name: 'New subscription' }));
  await user.click(form.getByRole('button', { name: 'Create subscription' }));
  expect(form.getByText('Check these fields before saving:')).toBeVisible();
  expect(
    form.getByRole('link', { name: /Subscription name: Enter a subscription name/ }),
  ).toHaveAttribute('href', '#subscription-name');
  expect(form.getByLabelText('Subscription name')).toHaveFocus();
  expect(writes).toBe(0);
});

it('brings an edited subscription into focus, opens its invalid advanced scope and restores row focus', async () => {
  server.use(
    http.get('/api/schedules', () =>
      HttpResponse.json({ items: [{ ...schedule, plan_id: 'missing-plan' }] }),
    ),
  );
  const { user } = renderApp('/research/recurring', 'user');
  const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
  const edit = table.getByRole('button', { name: 'Edit' });
  await user.click(edit);
  const form = within(await screen.findByRole('form', { name: 'Edit subscription' }));
  expect(form.getByRole('heading', { name: 'Edit subscription' })).toHaveFocus();
  const advanced = form.getByText('Advanced scope and sources').closest('details');
  expect(advanced).not.toHaveAttribute('open');
  await user.click(form.getByRole('button', { name: 'Save changes' }));
  expect(form.getByRole('link', { name: /Collection plan: Choose an available/ })).toBeVisible();
  expect(advanced).toHaveAttribute('open');
  expect(form.getByLabelText('Collection plan')).toHaveFocus();
  await user.click(form.getByRole('button', { name: 'Cancel' }));
  expect(edit).toHaveFocus();
});

it('requires a named archive confirmation and restores focus when cancelled', async () => {
  let deletes = 0;
  server.use(
    http.delete('/api/schedules/:id', () => {
      deletes += 1;
      return new HttpResponse(null, { status: 204 });
    }),
  );
  const { user } = renderApp('/research/recurring', 'user');
  const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
  const remove = table.getByRole('button', { name: 'Archive' });
  await user.click(remove);
  expect(deletes).toBe(0);
  expect(table.getByRole('group', { name: `Archive ${schedule.name}` })).toHaveTextContent(
    'Future runs stop. Existing reports remain available.',
  );
  expect(table.getByRole('button', { name: 'Confirm archive' })).toHaveFocus();
  await user.click(table.getByRole('button', { name: 'Cancel archiving' }));
  expect(table.queryByRole('button', { name: 'Confirm archive' })).not.toBeInTheDocument();
  expect(table.getByRole('button', { name: 'Archive' })).toHaveFocus();
  expect(deletes).toBe(0);
});

it('creates a paused, editable copy without updating the source subscription', async () => {
  let created: unknown = null;
  let updates = 0;
  server.use(
    http.get('/api/schedules', () => HttpResponse.json({ items: [schedule] })),
    http.post('/api/schedules', async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      created = body;
      return HttpResponse.json(
        { ...schedule, id: 'd1d1d1d1-d1d1-4d1d-8d1d-d1d1d1d1d1d1', ...body },
        { status: 201 },
      );
    }),
    http.put('/api/schedules/:id', () => {
      updates += 1;
      return HttpResponse.json(schedule);
    }),
  );
  const { user } = renderApp('/research/recurring', 'user');
  const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
  await user.click(table.getByRole('button', { name: 'Duplicate' }));
  const form = within(await screen.findByRole('form', { name: 'Duplicate subscription' }));
  expect(form.getByLabelText('Subscription name')).toHaveValue('Copy of Morning INTSUM');
  expect(form.getByText(/This subscription remains paused until you resume it/)).toBeVisible();
  await user.click(form.getByRole('button', { name: 'Create copy' }));
  await waitFor(() => {
    expect(created).toMatchObject({
      name: 'Copy of Morning INTSUM',
      enabled: false,
      cadence: schedule.cadence,
      country_iso: schedule.country_iso,
    });
  });
  expect(updates).toBe(0);
});

it('copies a linked subscription from its exact brief revision and leaves the copy paused', async () => {
  const briefId = 'd73c2988-d2ca-4482-9e39-7269e876eaa0';
  const linked = {
    ...schedule,
    brief_id: briefId,
    brief_revision: 2,
    timezone: 'Europe/London',
    local_hour: 8,
    local_minute: 30,
  };
  const draft = newBriefDraft();
  draft.title = 'Port watch';
  draft.question.main = 'What changed at the port?';
  const brief = {
    ...draft,
    identity: {
      id: briefId,
      revision: 2,
      owner_id: linked.created_by,
      team_id: null,
      title: draft.title,
      created_at: linked.created_at,
      revised_at: linked.created_at,
      preset_id: null,
      preset_version: null,
      schema_version: 1,
      origin: 'authored',
      published: false,
    },
  };
  let submitted: Record<string, unknown> | null = null;
  let updates = 0;
  server.use(
    http.get('/api/schedules', () => HttpResponse.json({ items: [linked] })),
    http.get(`/api/research/briefs/${briefId}/revisions/2`, () => HttpResponse.json({ brief })),
    http.post('/api/schedules/from-brief', async ({ request }) => {
      submitted = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json(
        { ...linked, ...submitted, id: 'd1d1d1d1-d1d1-4d1d-8d1d-d1d1d1d1d1d1' },
        { status: 201 },
      );
    }),
    http.put('/api/schedules/:id', () => {
      updates += 1;
      return HttpResponse.json(linked);
    }),
  );
  const { user } = renderApp('/research/recurring', 'user');
  const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
  const duplicate = table.getByRole('button', { name: 'Duplicate' });
  await user.click(duplicate);
  const form = within(
    await screen.findByRole('form', { name: 'Duplicate Research Brief subscription' }),
  );
  expect(form.getByText(/Revision 2/)).toBeVisible();
  expect(form.getByLabelText('Subscription name')).toHaveValue('Copy of Morning INTSUM');
  expect(form.getByLabelText('IANA timezone')).toHaveValue('Europe/London');
  expect(form.getByLabelText('Local time')).toHaveValue('08:30');
  await user.click(form.getByRole('button', { name: 'Create paused copy' }));
  await waitFor(() =>
    expect(submitted).toMatchObject({
      brief_id: briefId,
      brief_revision: 2,
      name: 'Copy of Morning INTSUM',
      enabled: false,
      cadence: 'daily',
      timezone: 'Europe/London',
      local_hour: 8,
      local_minute: 30,
    }),
  );
  expect(updates).toBe(0);
  expect(
    await screen.findByText(/Paused copy created from the exact Research Brief revision/),
  ).toBeVisible();
  expect(duplicate).toHaveFocus();
});
