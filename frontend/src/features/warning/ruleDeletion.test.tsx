import { screen, waitFor, within } from '@testing-library/react';
import { delay, http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { indicator } from '@/test/fixtures';
import { installDialogStub } from '@/test/dialogStub';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

installDialogStub();

const TITLE = `Delete alert rule “${indicator.name}”?`;

function trackDeletes(respond: () => Response | Promise<Response>) {
  const calls = { count: 0, listed: [indicator] };
  server.use(
    http.get('/api/warning/indicators', () => HttpResponse.json({ items: calls.listed })),
    http.delete('/api/warning/indicators/:id', () => {
      calls.count += 1;
      return respond();
    }),
  );
  return calls;
}

async function openRule() {
  const { user } = renderApp('/warning', 'user');
  const table = await screen.findByRole('table', { name: 'Alert rules' });
  const trigger = within(table).getByRole('button', { name: `Delete ${indicator.name}` });
  await user.click(trigger);
  const dialog = await screen.findByRole('alertdialog', { name: TITLE });
  return { user, trigger, dialog };
}

describe('alert rule deletion', () => {
  it('describes the rule and its workspace, and Cancel or Escape sends nothing', async () => {
    const calls = trackDeletes(() => new HttpResponse(null, { status: 204 }));
    const { user, trigger, dialog } = await openRule();
    expect(dialog).toHaveTextContent('Personal');
    expect(dialog).toHaveTextContent('stops raising new alerts');
    expect(dialog).toHaveTextContent('cannot be undone');
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    await waitFor(() => {
      expect(trigger).toHaveFocus();
    });
    await user.click(trigger);
    await screen.findByRole('alertdialog', { name: TITLE });
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'Alert rules' })).toHaveTextContent(indicator.name);
    expect(calls.count).toBe(0);
  });

  it('deletes once, refreshes the rules and moves focus to their heading', async () => {
    const calls = trackDeletes(async () => {
      await delay(150);
      calls.listed = [];
      return new HttpResponse(null, { status: 204 });
    });
    const { user, dialog } = await openRule();
    const confirm = within(dialog).getByRole('button', { name: 'Delete rule' });
    await user.click(confirm);
    await user.click(confirm);
    expect(await screen.findByText('No alert rules yet')).toBeInTheDocument();
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(calls.count).toBe(1);
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Alert rules' })).toHaveFocus();
    });
  });

  it('keeps the rule and a refusal visible, and allows a retry', async () => {
    const calls = trackDeletes(() => apiError(403, 'forbidden', 'You cannot change this rule.'));
    const { user, dialog } = await openRule();
    await user.click(within(dialog).getByRole('button', { name: 'Delete rule' }));
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(
      'You cannot change this rule.',
    );
    expect(await screen.findByRole('table', { name: 'Alert rules' })).toHaveTextContent(
      indicator.name,
    );
    expect(within(dialog).getByRole('button', { name: 'Delete rule' })).toBeEnabled();
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(calls.count).toBe(1);
  });
});
