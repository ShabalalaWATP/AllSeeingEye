import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import type { Indicator } from '@/lib/api/warning';
import { indicator } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const stalePlan = 'a0a0a0a0-a0a0-4a0a-8a0a-a0a0a0a0a0a0';

function serveRule(rule: Indicator) {
  const bodies: Record<string, unknown>[] = [];
  server.use(
    http.get('/api/warning/indicators', () => HttpResponse.json({ items: [rule] })),
    http.put('/api/warning/indicators/:id', async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      bodies.push(body);
      return HttpResponse.json({ ...rule, plan_id: body.plan_id ?? null });
    }),
  );
  return bodies;
}

async function openEdit(rule: Indicator) {
  const view = renderApp('/warning', 'user');
  const table = await screen.findByRole('table', { name: 'Alert rules' });
  await view.user.click(within(table).getByRole('button', { name: `Edit ${rule.name}` }));
  const form = await screen.findByRole('form', { name: `Edit alert rule ${rule.name}` });
  return { ...view, form: within(form) };
}

it('shows a deleted plan as unavailable and saves once the link is removed', async () => {
  const rule = { ...indicator, plan_id: stalePlan };
  const bodies = serveRule(rule);
  const { user, form } = await openEdit(rule);
  const select = form.getByRole('combobox', { name: /Collection plan/ });
  expect(select).toHaveDisplayValue('Unavailable plan');
  await user.selectOptions(select, 'No plan (remove link)');
  expect(form.queryByText(/The linked plan is no longer available/)).not.toBeInTheDocument();
  await user.click(form.getByRole('button', { name: 'Save changes' }));
  await waitFor(() => expect(bodies).toHaveLength(1));
  // An omitted plan saves the rule without one.
  expect(bodies[0]).not.toHaveProperty('plan_id');
});

it('treats a plan list that failed to load as unknown and keeps the saved link', async () => {
  const rule = { ...indicator, plan_id: stalePlan };
  const bodies = serveRule(rule);
  server.use(
    http.get('/api/direction/plans', () =>
      HttpResponse.json({ detail: 'Unavailable.' }, { status: 503 }),
    ),
  );
  const { user, form } = await openEdit(rule);
  const select = form.getByRole('combobox', { name: /Collection plan/ });
  expect(select).toHaveDisplayValue('Linked plan (list not loaded)');
  expect(form.queryByText(/The linked plan is no longer available/)).not.toBeInTheDocument();
  await user.click(form.getByRole('button', { name: 'Save changes' }));
  await waitFor(() => expect(bodies).toHaveLength(1));
  expect(bodies[0]?.plan_id).toBe(stalePlan);
});
