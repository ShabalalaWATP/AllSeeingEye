import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { alert, indicator } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { installDialogStub } from '@/test/dialogStub';

import { fillWorldwideRule } from './ruleTestSteps';

installDialogStub();

const failure = (message: string) =>
  HttpResponse.json({ error: { code: 'server_error', message } }, { status: 500 });

describe('warning states', () => {
  it('shows errors and empty lists', async () => {
    server.use(
      http.get('/api/warning/alerts', () => failure('Alerts boom')),
      http.get('/api/warning/indicators', () => HttpResponse.json({ items: [] })),
    );
    renderApp('/warning', 'user');
    expect(await screen.findAllByText('Alerts boom')).not.toHaveLength(0);
    expect(await screen.findByText('No alert rules yet')).toBeInTheDocument();
    expect(screen.getByText(/An alert rule watches connected feeds/)).toBeVisible();
    server.use(
      http.get('/api/warning/alerts', () => HttpResponse.json({ items: [], unacknowledged: 0 })),
      http.get('/api/warning/indicators', () => failure('Indicators boom')),
    );
    renderApp('/warning', 'user');
    expect(await screen.findByText('Nothing has fired in the last week.')).toBeInTheDocument();
    expect(await screen.findByText('Indicators boom')).toBeInTheDocument();
  });

  it('describes box and bare rules, bare alerts, and deletes an alert rule', async () => {
    let deleted: string | null = null;
    server.use(
      http.get('/api/warning/indicators', () =>
        HttpResponse.json({
          items: [
            {
              ...indicator,
              bbox: [30, 44, 41, 53],
              countries: [],
              keywords: [],
              categories: [],
              enabled: false,
              report_template: null,
            },
            {
              ...indicator,
              id: 'c9c9c9c9-c9c9-4c9c-8c9c-c9c9c9c9c9c9',
              countries: [],
              name: 'Anywhere',
            },
          ],
        }),
      ),
      http.get('/api/warning/alerts', () =>
        HttpResponse.json({
          items: [{ ...alert, summary: '', countries: [], report_id: null }],
          unacknowledged: 1,
        }),
      ),
      http.delete('/api/warning/indicators/:id', ({ params }) => {
        deleted = String(params.id);
        return new HttpResponse(null, { status: 204 });
      }),
      http.post('/api/warning/alerts/:id/ack', () => failure('Ack boom')),
    );
    const { user } = renderApp('/warning', 'user');
    const table = await screen.findByRole('table', { name: 'Alert rules' });
    expect(within(table).getByText('box 30.0, 44.0, 41.0, 53.0')).toBeInTheDocument();
    expect(within(table).getByText('2 or more any category in 6 hours')).toBeInTheDocument();
    expect(within(table).getByText('worldwide')).toBeInTheDocument();
    expect(within(table).getByText('Paused: not evaluated, raises no alerts')).toBeVisible();
    expect(within(table).getByText('none')).toBeInTheDocument();
    const list = screen.getByRole('list', { name: 'Alerts' });
    expect(within(list).queryByRole('link', { name: 'Report' })).not.toBeInTheDocument();
    await user.click(within(list).getByRole('button', { name: 'Acknowledge' }));
    expect(await screen.findByText('Ack boom')).toBeInTheDocument();
    await user.click(within(table).getAllByRole('button', { name: /^Delete/ })[0]!);
    await user.click(
      within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Delete rule' }),
    );
    await waitFor(() => {
      expect(deleted).toBe(indicator.id);
    });
  });

  it('blocks a blank threshold with an inline problem and sends nothing', async () => {
    let captured: unknown = null;
    server.use(
      http.post('/api/warning/indicators', async ({ request }) => {
        captured = await request.json();
        return HttpResponse.json(indicator, { status: 201 });
      }),
    );
    const { user } = renderApp('/warning', 'user');
    const form = await screen.findByRole('form', { name: 'New alert rule' });
    await fillWorldwideRule(user, within(form), 'Blank threshold');
    await user.clear(within(form).getByLabelText('Threshold'));
    await user.click(within(form).getByRole('button', { name: 'Add alert rule' }));
    const summary = await within(form).findByRole('alert', {
      name: 'Check these fields and try again:',
    });
    expect(summary).toHaveTextContent('Threshold: Enter a whole number from 1 to 10000.');
    expect(within(form).getByLabelText('Threshold')).toHaveAttribute('aria-invalid', 'true');
    expect(captured).toBeNull();
    await user.type(within(form).getByLabelText('Threshold'), '1');
    await user.click(within(form).getByRole('button', { name: 'Add alert rule' }));
    await waitFor(() => {
      expect(captured).toMatchObject({
        name: 'Blank threshold',
        threshold: 1,
        countries: [],
        report_template: null,
      });
    });
  });
});
