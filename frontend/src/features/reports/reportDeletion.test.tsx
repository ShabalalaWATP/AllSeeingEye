import { screen, waitFor, within } from '@testing-library/react';
import { delay, http, HttpResponse } from 'msw';
import { beforeAll, describe, expect, it } from 'vitest';

import { report, reportSummary } from '@/test/fixtures';
import { installDialogStub } from '@/test/dialogStub';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

installDialogStub();

beforeAll(async () => {
  await Promise.all([import('./SavedResearchPage'), import('./ReportPage')]);
});

const TITLE = `Delete report “${reportSummary.title}”?`;

function countDeletes(respond: () => Response | Promise<Response>) {
  const calls = { count: 0 };
  server.use(
    http.get('/api/reports/:id', () =>
      HttpResponse.json({ ...report, report: { ...reportSummary, latest_version: 3 } }),
    ),
    http.delete('/api/reports/:id', () => {
      calls.count += 1;
      return respond();
    }),
  );
  return calls;
}

async function openManagement() {
  const rendered = renderApp(`/reports/${reportSummary.id}`, 'user');
  const { user } = rendered;
  await user.click(await screen.findByRole('button', { name: 'Sources & methods' }));
  await user.click(await screen.findByRole('button', { name: 'Review' }));
  const management = await screen.findByRole('region', { name: 'Report management' });
  return { user, management };
}

describe('report deletion', () => {
  it('names the report, its scope and what is removed, and Cancel sends nothing', async () => {
    const calls = countDeletes(() => new HttpResponse(null, { status: 204 }));
    const { user, management } = await openManagement();
    const trigger = within(management).getByRole('button', { name: 'Delete report' });
    await user.click(trigger);
    const dialog = await screen.findByRole('alertdialog', { name: TITLE });
    expect(dialog).toHaveTextContent('Personal');
    expect(dialog).toHaveTextContent('all 3 saved versions');
    expect(dialog).toHaveTextContent('frozen evidence');
    expect(dialog).toHaveTextContent('cannot be undone');
    expect(within(dialog).getByRole('button', { name: 'Cancel' })).toHaveFocus();
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    await waitFor(() => {
      expect(trigger).toHaveFocus();
    });
    await user.click(trigger);
    await screen.findByRole('alertdialog', { name: TITLE });
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    // Escape closed only the confirmation, not the supporting workspace behind it.
    expect(screen.getByRole('region', { name: 'Report management' })).toBeInTheDocument();
    expect(calls.count).toBe(0);
  });

  it('keeps a failed deletion in the confirmation with a retry, then deletes once and leaves', async () => {
    let fail = true;
    const calls = countDeletes(async () => {
      await delay(150);
      return fail
        ? apiError(503, 'unavailable', 'The database is busy. Try again.')
        : new HttpResponse(null, { status: 204 });
    });
    const { user, management } = await openManagement();
    await user.click(within(management).getByRole('button', { name: 'Delete report' }));
    const dialog = await screen.findByRole('alertdialog', { name: TITLE });
    const confirm = within(dialog).getByRole('button', { name: 'Delete report' });
    await user.click(confirm);
    await user.click(confirm);
    expect(confirm).toHaveAttribute('aria-busy', 'true');
    expect(confirm).toHaveTextContent('Deleting report…');
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('The database is busy.');
    expect(calls.count).toBe(1);
    fail = false;
    await user.click(confirm);
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Saved research' }),
    ).toBeInTheDocument();
    expect(calls.count).toBe(2);
  });

  it('keeps the report and the refusal visible after a forbidden deletion', async () => {
    const calls = countDeletes(() => apiError(403, 'forbidden', 'You cannot delete this report.'));
    const { user, management } = await openManagement();
    await user.click(within(management).getByRole('button', { name: 'Delete report' }));
    const dialog = await screen.findByRole('alertdialog', { name: TITLE });
    await user.click(within(dialog).getByRole('button', { name: 'Delete report' }));
    // A refusal reloads the report under fresh access, then shows the error beside a retry.
    expect(await screen.findByRole('alert')).toHaveTextContent('You cannot delete this report.');
    expect(
      screen.getByRole('heading', { level: 1, name: reportSummary.title }),
    ).toBeInTheDocument();
    const retry = within(screen.getByRole('region', { name: 'Report management' })).getByRole(
      'button',
      { name: 'Delete report' },
    );
    expect(retry).toBeEnabled();
    expect(calls.count).toBe(1);
  });

  it('shows why a report in a subscription edition history cannot be deleted', async () => {
    const message =
      "This report is part of a subscription's saved edition history, so it cannot be deleted.";
    const calls = countDeletes(() => apiError(409, 'conflict', message));
    const { user, management } = await openManagement();
    await user.click(within(management).getByRole('button', { name: 'Delete report' }));
    const dialog = await screen.findByRole('alertdialog', { name: TITLE });
    expect(dialog).toHaveTextContent("A report kept in a subscription's edition history");
    await user.click(within(dialog).getByRole('button', { name: 'Delete report' }));
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(message);
    expect(
      screen.getByRole('heading', { level: 1, name: reportSummary.title }),
    ).toBeInTheDocument();
    expect(calls.count).toBe(1);
  });
});
