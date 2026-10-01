import { screen, waitFor, within } from '@testing-library/react';
import { delay, http, HttpResponse } from 'msw';
import { beforeAll, describe, expect, it } from 'vitest';

import { aoi, plan } from '@/test/fixtures';
import { installDialogStub } from '@/test/dialogStub';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

installDialogStub();

beforeAll(async () => {
  await Promise.all([import('./DirectionPage'), import('./PlanPage')]);
});

const AREA = `Delete area “${aoi.name}”?`;
const PLAN = `Delete collection plan “${plan.name}”?`;

function track(path: string, respond: () => Response | Promise<Response>) {
  const calls = { count: 0 };
  server.use(
    http.delete(path, () => {
      calls.count += 1;
      return respond();
    }),
  );
  return calls;
}

describe('saved area deletion', () => {
  async function openArea() {
    const { user } = renderApp('/direction', 'user');
    const table = await screen.findByRole('table', { name: 'Areas of interest' });
    const trigger = within(table).getByRole('button', { name: 'Delete' });
    await user.click(trigger);
    const dialog = await screen.findByRole('alertdialog', { name: AREA });
    return { user, trigger, dialog };
  }

  it('names the area and its effect on plans, and Cancel or Escape sends nothing', async () => {
    const calls = track('/api/direction/aois/:id', () => new HttpResponse(null, { status: 204 }));
    const { user, trigger, dialog } = await openArea();
    expect(dialog).toHaveTextContent('Personal');
    expect(dialog).toHaveTextContent('box 30.0, 44.0, 41.0, 53.0');
    expect(dialog).toHaveTextContent('Collection plans that use this area');
    expect(dialog).toHaveTextContent('cannot be undone');
    await user.keyboard('{Escape}');
    await waitFor(() => {
      expect(trigger).toHaveFocus();
    });
    await user.click(trigger);
    await user.click(
      within(await screen.findByRole('alertdialog', { name: AREA })).getByRole('button', {
        name: 'Cancel',
      }),
    );
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(calls.count).toBe(0);
  });

  it('deletes once, refreshes the list and moves focus to the areas heading', async () => {
    let listed = [aoi];
    server.use(http.get('/api/direction/aois', () => HttpResponse.json({ items: listed })));
    const calls = track('/api/direction/aois/:id', async () => {
      await delay(150);
      listed = [];
      return new HttpResponse(null, { status: 204 });
    });
    const { user, dialog } = await openArea();
    const confirm = within(dialog).getByRole('button', { name: 'Delete area' });
    await user.click(confirm);
    await user.click(confirm);
    expect(await screen.findByText('No areas of interest yet')).toBeInTheDocument();
    expect(calls.count).toBe(1);
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Areas of interest' })).toHaveFocus();
    });
  });

  it('keeps the area and a refusal visible beside a retry', async () => {
    const calls = track('/api/direction/aois/:id', () =>
      apiError(403, 'forbidden', 'You cannot delete this area.'),
    );
    const { user, dialog } = await openArea();
    await user.click(within(dialog).getByRole('button', { name: 'Delete area' }));
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(
      'You cannot delete this area.',
    );
    expect(await screen.findByRole('table', { name: 'Areas of interest' })).toHaveTextContent(
      aoi.name,
    );
    await user.click(within(dialog).getByRole('button', { name: 'Delete area' }));
    await waitFor(() => {
      expect(calls.count).toBe(2);
    });
  });
});

describe('collection plan deletion', () => {
  async function openPlan() {
    const { user } = renderApp(`/direction/plans/${plan.id}`, 'user');
    const trigger = await screen.findByRole('button', { name: 'Delete plan' });
    await user.click(trigger);
    const dialog = await screen.findByRole('alertdialog', { name: PLAN });
    return { user, trigger, dialog };
  }

  it('states what the plan holds, and Cancel sends nothing', async () => {
    const calls = track('/api/direction/plans/:id', () => new HttpResponse(null, { status: 204 }));
    const { user, trigger, dialog } = await openPlan();
    expect(dialog).toHaveTextContent('Personal');
    expect(dialog).toHaveTextContent('1 priority and 2 specific requirements');
    expect(dialog).toHaveTextContent('cannot be undone');
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    await waitFor(() => {
      expect(trigger).toHaveFocus();
    });
    expect(screen.getByRole('heading', { level: 1, name: plan.name })).toBeInTheDocument();
    expect(calls.count).toBe(0);
  });

  it('keeps a failure in the confirmation, then deletes once and returns to Direction', async () => {
    let fail = true;
    const calls = track('/api/direction/plans/:id', async () => {
      await delay(150);
      return fail
        ? apiError(503, 'unavailable', 'Storage is busy. Try again.')
        : new HttpResponse(null, { status: 204 });
    });
    const { user, dialog } = await openPlan();
    const confirm = within(dialog).getByRole('button', { name: 'Delete plan' });
    await user.click(confirm);
    await user.click(confirm);
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Storage is busy.');
    expect(calls.count).toBe(1);
    fail = false;
    await user.click(confirm);
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Plans and areas' }),
    ).toBeInTheDocument();
    expect(calls.count).toBe(2);
  });
});
