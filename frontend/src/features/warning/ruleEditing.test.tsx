import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import type { Indicator } from '@/lib/api/warning';
import { indicator } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { chooseCountry } from './ruleTestSteps';

const saved: Indicator = {
  ...indicator,
  description: 'Kept from the weekly assessment.',
  severity_floor: 0.4,
  cooldown_minutes: 90,
};

/** A list that reflects each accepted edit, and every request body the page sent. */
function rulesApi(initial: Indicator, respond?: (body: Record<string, unknown>) => Response) {
  const state = { rule: initial, bodies: [] as Record<string, unknown>[] };
  server.use(
    http.get('/api/warning/indicators', () => HttpResponse.json({ items: [state.rule] })),
    http.put('/api/warning/indicators/:id', async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      state.bodies.push(body);
      const refusal = respond?.(body);
      if (refusal) return refusal;
      const { expected_updated_at: _, confirm_wider_scope: __, ...values } = body;
      state.rule = { ...state.rule, ...values, updated_at: '2026-09-04T11:00:00Z' };
      return HttpResponse.json(state.rule);
    }),
  );
  return state;
}

async function openEdit(rule: Indicator = saved) {
  const view = renderApp('/warning', 'user');
  const table = await screen.findByRole('table', { name: 'Alert rules' });
  await view.user.click(within(table).getByRole('button', { name: `Edit ${rule.name}` }));
  const form = await screen.findByRole('form', { name: `Edit alert rule ${rule.name}` });
  return { ...view, form: within(form), table: within(table) };
}

describe('editing, pausing and resuming alert rules', () => {
  it('summarises a new rule and keeps every saved value through an edit', async () => {
    const api = rulesApi(saved);
    const { user, form } = await openEdit();
    expect(form.getByLabelText('Alert rule name')).toHaveValue('Kharkiv strikes');
    expect(form.getByRole('button', { name: 'Remove Ukraine' })).toBeVisible();
    expect(form.getByRole('checkbox', { name: 'Conflict & unrest' })).toBeChecked();
    expect(form.getByLabelText('Cooldown (minutes)')).toHaveValue(90);
    expect(form.getByLabelText('Severity floor')).toHaveValue(0.4);
    const summary = form.getByRole('region', { name: 'Before you save: this alert rule will' });
    expect(summary).toHaveTextContent('GeographyUkraine (UA)');
    expect(summary).toHaveTextContent('Severity floorOnly items rated 0.4 or higher');
    expect(summary).toHaveTextContent('Cooldown90 minutes between alerts');
    expect(summary).toHaveTextContent('Time windowThe last 6 hours');
    await user.clear(form.getByLabelText('Threshold'));
    await user.type(form.getByLabelText('Threshold'), '5');
    await user.click(form.getByRole('button', { name: 'Save changes' }));
    expect(await screen.findByText('Changes to “Kharkiv strikes” saved.')).toBeVisible();
    expect(api.bodies).toEqual([
      {
        name: 'Kharkiv strikes',
        description: 'Kept from the weekly assessment.',
        countries: ['UA'],
        categories: ['conflict'],
        keywords: ['Kharkiv', 'shelling'],
        threshold: 5,
        baseline_ratio: null,
        baseline_days: 30,
        window_minutes: 360,
        cooldown_minutes: 90,
        severity_floor: 0.4,
        report_template: 'intsum',
        enabled: true,
        expected_updated_at: saved.updated_at,
        confirm_wider_scope: false,
      },
    ]);
  });

  it('shows unknown retained values inline and refuses to save until they are removed', async () => {
    const api = rulesApi({ ...saved, countries: ['UA', 'XX'], categories: ['conflict', 'bogus'] });
    const { user, form } = await openEdit();
    expect(form.getByText('Remove unknown countries: XX.')).toBeVisible();
    expect(form.getByText('Remove unknown categories: bogus.')).toBeVisible();
    await user.click(form.getByRole('button', { name: 'Save changes' }));
    const problems = await form.findByRole('alert', { name: 'Check these fields and try again:' });
    expect(problems).toHaveTextContent('Watch location: Remove unknown countries: XX.');
    expect(api.bodies).toEqual([]);
    await user.click(form.getByRole('button', { name: 'Remove Unavailable country: XX' }));
    await user.click(form.getByRole('button', { name: 'Remove unknown category “bogus”' }));
    await user.click(form.getByRole('button', { name: 'Save changes' }));
    await waitFor(() => expect(api.bodies).toHaveLength(1));
    expect(api.bodies[0]).toMatchObject({ countries: ['UA'], categories: ['conflict'] });
  });

  it('needs an explicit confirmation before an edit removes a restriction', async () => {
    const api = rulesApi(saved);
    const { user, form } = await openEdit();
    await user.selectOptions(form.getByLabelText('Location scope'), 'worldwide');
    await user.click(form.getByRole('radio', { name: 'All event categories' }));
    await user.click(form.getByRole('button', { name: 'Save changes' }));
    expect(
      await form.findByRole('alert', { name: 'Check these fields and try again:' }),
    ).toHaveTextContent('Confirm wider scope');
    expect(api.bodies).toEqual([]);
    await user.click(
      form.getByRole('checkbox', {
        name: 'I understand this alert rule will no longer be restricted by location, category.',
      }),
    );
    await user.click(form.getByRole('button', { name: 'Save changes' }));
    await waitFor(() => expect(api.bodies).toHaveLength(1));
    expect(api.bodies[0]).toMatchObject({
      countries: [],
      categories: [],
      confirm_wider_scope: true,
    });
  });

  it('pauses and resumes with the saved values and says what pausing means', async () => {
    const api = rulesApi(saved);
    const { user } = renderApp('/warning', 'user');
    const table = within(await screen.findByRole('table', { name: 'Alert rules' }));
    await user.click(table.getByRole('button', { name: 'Pause Kharkiv strikes' }));
    expect(
      await screen.findByText(
        '“Kharkiv strikes” paused. It is not evaluated and raises no alerts until resumed.',
      ),
    ).toBeVisible();
    expect(await table.findByText('Paused: not evaluated, raises no alerts')).toBeVisible();
    await user.click(table.getByRole('button', { name: 'Resume Kharkiv strikes' }));
    expect(
      await screen.findByText('“Kharkiv strikes” resumed. It counts only activity from now on.'),
    ).toBeVisible();
    expect(api.bodies.map((body) => body.enabled)).toEqual([false, true]);
    expect(api.bodies[0]).toMatchObject({
      countries: ['UA'],
      keywords: ['Kharkiv', 'shelling'],
      cooldown_minutes: 90,
      expected_updated_at: saved.updated_at,
    });
    expect(api.bodies[1]).toMatchObject({ expected_updated_at: '2026-09-04T11:00:00Z' });
  });

  it('keeps entered values after a stale edit and offers the latest version', async () => {
    rulesApi(saved, () =>
      HttpResponse.json(
        {
          error: { code: 'conflict', message: 'This alert rule was changed after you opened it.' },
        },
        { status: 409 },
      ),
    );
    const { user, form } = await openEdit();
    await user.clear(form.getByLabelText('Alert rule name'));
    await user.type(form.getByLabelText('Alert rule name'), 'Renamed');
    await user.click(form.getByRole('button', { name: 'Save changes' }));
    expect(await form.findByText('This alert rule was changed after you opened it.')).toBeVisible();
    expect(form.getByLabelText('Alert rule name')).toHaveValue('Renamed');
    expect(screen.queryByText(/saved\.$/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reload the latest alert rules' })).toBeVisible();
  });

  it('blocks a missing linked plan with an actionable message', async () => {
    const api = rulesApi({ ...saved, plan_id: 'a0a0a0a0-a0a0-4a0a-8a0a-a0a0a0a0a0a0' });
    const { user, form } = await openEdit();
    expect(form.getByText(/The linked plan is no longer available/)).toBeVisible();
    await user.click(form.getByRole('button', { name: 'Save changes' }));
    expect(
      await form.findByRole('alert', { name: 'Check these fields and try again:' }),
    ).toHaveTextContent('Collection plan: The linked plan is unavailable.');
    expect(api.bodies).toEqual([]);
  });

  it('sends a new rule once, shows success only after the server confirms', async () => {
    const bodies: unknown[] = [];
    let release: () => void = () => undefined;
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.post('/api/warning/indicators', async ({ request }) => {
        bodies.push(await request.json());
        await held;
        return HttpResponse.json({ ...indicator, name: 'Sumy watch' }, { status: 201 });
      }),
    );
    const { user } = renderApp('/warning', 'user');
    const form = within(await screen.findByRole('form', { name: 'New alert rule' }));
    await user.type(form.getByLabelText('Alert rule name'), 'Sumy watch');
    await chooseCountry(user, form, 'Ukraine');
    const add = form.getByRole('button', { name: 'Add alert rule' });
    await user.click(add);
    await user.click(add);
    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(screen.queryByText('Alert rule “Sumy watch” added.')).not.toBeInTheDocument();
    release();
    expect(await screen.findByText('Alert rule “Sumy watch” added.')).toBeVisible();
    expect(bodies).toHaveLength(1);
  });

  it('keeps entered values when a new rule is refused', async () => {
    server.use(
      http.post('/api/warning/indicators', () =>
        HttpResponse.json({ error: { code: 'server_error', message: 'Boom' } }, { status: 500 }),
      ),
    );
    const { user } = renderApp('/warning', 'user');
    const form = within(await screen.findByRole('form', { name: 'New alert rule' }));
    await user.type(form.getByLabelText('Alert rule name'), 'Kept name');
    await user.selectOptions(form.getByLabelText('Location scope'), 'worldwide');
    await user.click(form.getByRole('button', { name: 'Add alert rule' }));
    expect(await form.findByText('Boom')).toBeVisible();
    expect(form.getByLabelText('Alert rule name')).toHaveValue('Kept name');
    expect(form.getByLabelText('Location scope')).toHaveValue('worldwide');
  });
});
