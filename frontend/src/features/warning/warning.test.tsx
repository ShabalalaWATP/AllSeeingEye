import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { indicator } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('warning', () => {
  it('shows the alerts and acknowledges one', async () => {
    const { user } = renderApp('/warning', 'user');
    const list = await screen.findByRole('list', { name: 'Alerts' });
    const items = within(list).getAllByRole('listitem');
    expect(items).toHaveLength(2);
    expect(within(items[0]!).getByText('Kharkiv strikes: 3 items in the last 6 h')).toBeVisible();
    expect(within(items[0]!).getByRole('link', { name: 'Report' })).toHaveAttribute(
      'href',
      '/reports/11111111-1111-4111-8111-111111111111',
    );
    expect(within(items[1]!).getByText('acknowledged')).toBeInTheDocument();
    await user.click(within(items[0]!).getByRole('button', { name: 'Acknowledge' }));
    await waitFor(() => {
      expect(within(items[0]!).getByText('acknowledged')).toBeInTheDocument();
    });
  });

  it('lists indicators with their rule and creates one from the form', async () => {
    let captured: unknown = null;
    server.use(
      http.post('/api/warning/indicators', async ({ request }) => {
        captured = await request.json();
        return HttpResponse.json(indicator, { status: 201 });
      }),
    );
    const { user } = renderApp('/warning', 'user');
    const table = await screen.findByRole('table', { name: 'Indicators' });
    expect(within(table).getByText('Kharkiv strikes')).toBeInTheDocument();
    expect(
      within(table).getByText('2 or more conflict with Kharkiv, shelling in 6 h'),
    ).toBeVisible();
    expect(within(table).getByText('intsum')).toBeInTheDocument();

    const form = screen.getByRole('form', { name: 'New indicator' });
    await user.type(within(form).getByLabelText('Indicator name'), 'Sumy strikes');
    await user.type(within(form).getByLabelText('Nations'), 'ua');
    await user.type(within(form).getByLabelText('Categories'), 'conflict, bogus');
    await user.type(within(form).getByLabelText('Keywords'), 'Sumy, strike');
    await user.clear(within(form).getByLabelText('Threshold'));
    await user.type(within(form).getByLabelText('Threshold'), '3');
    await user.selectOptions(within(form).getByLabelText('Window'), '1440');
    await user.selectOptions(within(form).getByLabelText('Report when it fires'), 'intsum');
    await user.click(within(form).getByRole('button', { name: 'Add indicator' }));
    await waitFor(() => {
      expect(captured).toEqual({
        name: 'Sumy strikes',
        description: '',
        enabled: true,
        cooldown_minutes: 60,
        severity_floor: 0,
        countries: ['UA'],
        keywords: ['Sumy', 'strike'],
        categories: ['conflict'],
        threshold: 3,
        window_minutes: 1440,
        report_template: 'intsum',
      });
    });
  });

  it('offers alerts from the monitoring group of the rail as well as personal settings', async () => {
    const { user } = renderApp('/settings', 'user');
    const alerts = await within(screen.getByRole('main')).findByRole('link', {
      name: /^Alerts & rules/,
    });
    expect(alerts).toHaveAttribute('href', '/warning');
    const primary = within(screen.getByRole('navigation', { name: 'Primary' }));
    expect(primary.getByRole('link', { name: 'Alerts & rules' })).toHaveAttribute(
      'href',
      '/warning',
    );
    expect(screen.queryByRole('link', { name: /unacknowledged/ })).not.toBeInTheDocument();
    await user.click(alerts);
    const list = await screen.findByRole('list', { name: 'Alerts' });
    expect(within(list).getAllByRole('listitem')).toHaveLength(2);
  });
});
