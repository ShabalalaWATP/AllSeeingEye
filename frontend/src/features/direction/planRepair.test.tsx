import { render, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import type { CollectionPlan } from '@/lib/api/direction';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';
import { plan } from '@/test/fixtures';
import { installDialogStub } from '@/test/dialogStub';
import { planEvidence } from '@/test/fixtures.direction';
import { apiError } from '@/test/handlers.responses';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { PlanForm } from './PlanForm';

installDialogStub();

const deletedArea = 'dededede-dede-4ede-8ede-dededededede';
const broken: CollectionPlan = { ...plan, aoi_id: deletedArea };

function serveBrokenPlan() {
  let repaired = false;
  const bodies: Record<string, unknown>[] = [];
  server.use(
    http.get('/api/direction/plans/:id', () =>
      repaired
        ? HttpResponse.json({ ...planEvidence, aoi: null, plan: { ...plan, aoi_id: null } })
        : apiError(422, 'invalid_request', 'The linked area is unavailable; repair the plan.'),
    ),
    http.get('/api/direction/plans/:id/definition', () => HttpResponse.json(broken)),
    http.put('/api/direction/plans/:id', async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      bodies.push(body);
      repaired = true;
      return HttpResponse.json({ ...broken, aoi_id: null, updated_at: '2026-09-04T11:00:00Z' });
    }),
  );
  return bodies;
}

describe('a plan whose area was deleted', () => {
  it('keeps edit and delete beside the error so the plan can be repaired', async () => {
    const bodies = serveBrokenPlan();
    const { user } = renderApp(`/direction/plans/${plan.id}`, 'user');
    expect(await screen.findByText(/The linked area is unavailable/)).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: 'Delete plan' })).toBeEnabled();
    const edit = screen.getByRole('button', { name: 'Edit plan' });
    await waitFor(() => expect(edit).toBeEnabled());
    await user.click(edit);
    const form = within(await screen.findByRole('form', { name: `Edit ${plan.name}` }));
    const area = form.getByRole('combobox', { name: /Area/ });
    expect(area).toHaveDisplayValue('Unavailable area');
    expect(form.getByText(/The linked area is no longer available/)).toBeVisible();
    await user.selectOptions(area, 'No area (remove link)');
    await user.click(form.getByRole('button', { name: 'Save plan' }));
    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]?.aoi_id).toBeNull();
    expect(await screen.findByRole('heading', { name: plan.name })).toBeInTheDocument();
  });

  it('offers deletion of the unrepairable plan', async () => {
    serveBrokenPlan();
    const { user } = renderApp(`/direction/plans/${plan.id}`, 'user');
    await user.click(await screen.findByRole('button', { name: 'Delete plan' }));
    expect(
      await screen.findByRole('alertdialog', { name: `Delete collection plan “${plan.name}”?` }),
    ).toBeInTheDocument();
  });
});

it('treats an area list that is not loaded as unknown rather than a stale link', () => {
  const workspaces = {
    teams: [],
    key: 'k',
    loading: false,
    label: () => 'Personal',
  } as unknown as Workspaces;
  render(<PlanForm areas={null} workspaces={workspaces} plan={broken} onSaved={() => undefined} />);
  expect(screen.getByRole('combobox', { name: /Area/ })).toHaveDisplayValue(
    'Linked area (list not loaded)',
  );
  expect(screen.queryByText(/The linked area is no longer available/)).not.toBeInTheDocument();
});
