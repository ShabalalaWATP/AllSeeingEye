import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { aoi, plan } from '@/test/fixtures.direction';
import { roster, team } from '@/test/fixtures.teams';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const teamArea = {
  ...aoi,
  id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  name: 'Team area',
  team_id: team.id,
};
const teamPlan = {
  ...plan,
  id: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
  name: 'Team plan',
  team_id: team.id,
  aoi_id: teamArea.id,
};

function teams() {
  server.use(
    http.get('/api/teams', () => HttpResponse.json({ items: [team] })),
    http.get('/api/teams/:id', () => HttpResponse.json(roster)),
    http.get('/api/direction/aois', () => HttpResponse.json({ items: [aoi, teamArea] })),
    http.get('/api/direction/plans', () => HttpResponse.json({ items: [plan, teamPlan] })),
  );
}

describe('Personal and team creation', () => {
  it('defaults each form to Personal and never links a plan to another workspace area', async () => {
    teams();
    const writes: unknown[] = [];
    server.use(
      http.post('/api/direction/plans', async ({ request }) => {
        writes.push(await request.json());
        return HttpResponse.json(teamPlan, { status: 201 });
      }),
    );
    const { user } = renderApp('/direction', 'user');
    const form = await screen.findByRole('form', { name: 'New collection plan' });
    const areaForm = screen.getByRole('form', { name: 'New area of interest' });
    await within(form).findByRole('option', { name: 'Team: Northern desk' });
    expect(within(form).getByLabelText('Workspace')).toHaveValue('');
    expect(within(areaForm).getByLabelText('Workspace')).toHaveValue('');
    expect(within(form).queryByRole('option', { name: 'Team area' })).not.toBeInTheDocument();
    await user.selectOptions(within(form).getByLabelText('Area'), aoi.id);
    await user.selectOptions(within(form).getByLabelText('Workspace'), team.id);
    expect(within(form).getByLabelText('Area')).toHaveValue('');
    expect(within(form).queryByRole('option', { name: aoi.name })).not.toBeInTheDocument();
    await user.selectOptions(within(form).getByLabelText('Area'), teamArea.id);
    await user.type(within(form).getByLabelText('Plan name'), 'Shared watch');
    await user.type(
      within(form).getByLabelText('Priority intelligence requirement'),
      'What changed?',
    );
    await user.type(within(form).getByLabelText('Specific requirements'), 'Activity | movement');
    await user.click(within(form).getByRole('button', { name: 'Add plan' }));
    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]).toMatchObject({ team_id: team.id, aoi_id: teamArea.id });
    expect(within(areaForm).getByLabelText('Workspace')).toHaveValue('');
  });

  it('clears scoped records and form choices immediately when access changes', async () => {
    teams();
    const { user } = renderApp('/direction', 'user');
    const form = await screen.findByRole('form', { name: 'New collection plan' });
    await within(form).findByRole('option', { name: 'Team: Northern desk' });
    await user.selectOptions(within(form).getByLabelText('Workspace'), team.id);
    await user.type(within(form).getByLabelText('Plan name'), 'Private team draft');
    server.use(
      http.get('/api/teams', () => HttpResponse.json({ items: [] })),
      http.get('/api/direction/aois', () => HttpResponse.json({ items: [aoi] })),
      http.get('/api/direction/plans', () => HttpResponse.json({ items: [plan] })),
    );
    act(() => invalidateWorkspaceAccess());
    expect(screen.queryByText('Team plan')).not.toBeInTheDocument();
    const refreshed = screen.getByRole('form', { name: 'New collection plan' });
    expect(within(refreshed).getByLabelText('Workspace')).toHaveValue('');
    expect(within(refreshed).getByLabelText('Plan name')).toHaveValue('');
    await waitFor(() =>
      expect(
        within(refreshed).queryByRole('option', { name: 'Team: Northern desk' }),
      ).not.toBeInTheDocument(),
    );
  });

  it('submits matching team scope for reports, schedules and indicators', async () => {
    teams();
    const writes: Record<string, unknown>[] = [];
    for (const url of ['/api/reports', '/api/schedules', '/api/warning/indicators']) {
      server.use(
        http.post(url, async ({ request }) => {
          writes.push((await request.json()) as Record<string, unknown>);
          return apiError(409, 'test_stop', 'Recorded for validation.');
        }),
      );
    }
    const { user, router } = renderApp('/reports?template=intsum', 'user');
    const report = await screen.findByRole('form', { name: 'Generate a report' });
    await within(report).findByRole('option', { name: 'Team: Northern desk' });
    await user.selectOptions(within(report).getByLabelText('Workspace'), team.id);
    expect(within(report).queryByRole('option', { name: plan.name })).not.toBeInTheDocument();
    await user.selectOptions(within(report).getByLabelText('Collection plan'), teamPlan.id);
    await user.click(within(report).getByRole('button', { name: 'Generate' }));
    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]).toMatchObject({ team_id: team.id, plan: teamPlan.id });
    await act(async () => {
      await router.navigate('/research/recurring');
    });
    const schedule = await screen.findByRole('form', { name: 'New schedule' });
    await user.click(within(schedule).getByText('Advanced scope and sources'));
    await user.selectOptions(within(schedule).getByLabelText('Workspace'), team.id);
    await user.selectOptions(within(schedule).getByLabelText('Collection plan'), teamPlan.id);
    await user.type(within(schedule).getByLabelText('Schedule name'), 'Desk update');
    await user.type(within(schedule).getByLabelText('Question'), 'What changed in this area?');
    await user.click(within(schedule).getByRole('button', { name: 'Add schedule' }));
    await waitFor(() => expect(writes).toHaveLength(2));
    expect(writes[1]).toMatchObject({ team_id: team.id, plan_id: teamPlan.id });
    await act(async () => {
      await router.navigate('/warning');
    });
    const indicator = await screen.findByRole('form', { name: 'New indicator' });
    await within(indicator).findByRole('option', { name: 'Team: Northern desk' });
    await user.selectOptions(within(indicator).getByLabelText('Workspace'), team.id);
    await user.selectOptions(within(indicator).getByLabelText('Collection plan'), teamPlan.id);
    await user.type(within(indicator).getByLabelText('Indicator name'), 'Desk indicator');
    await user.click(within(indicator).getByRole('button', { name: 'Add indicator' }));
    await waitFor(() => expect(writes).toHaveLength(3));
    expect(writes[2]).toMatchObject({ team_id: team.id, plan_id: teamPlan.id });
  });
});
