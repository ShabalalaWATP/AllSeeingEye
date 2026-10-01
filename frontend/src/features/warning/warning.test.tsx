import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { indicator } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { chooseCountry } from './ruleTestSteps';

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

  it('lists alert rules with their rule and creates one from the form', async () => {
    let captured: unknown = null;
    server.use(
      http.post('/api/warning/indicators', async ({ request }) => {
        captured = await request.json();
        return HttpResponse.json(indicator, { status: 201 });
      }),
    );
    const { user } = renderApp('/warning', 'user');
    const table = await screen.findByRole('table', { name: 'Alert rules' });
    expect(within(table).getByText('Kharkiv strikes')).toBeInTheDocument();
    expect(
      within(table).getByText('2 or more conflict with Kharkiv, shelling in 6 hours'),
    ).toBeVisible();
    expect(within(table).getByText('intsum')).toBeInTheDocument();
    expect(within(table).getByText('Active')).toBeInTheDocument();

    const form = screen.getByRole('form', { name: 'New alert rule' });
    await user.type(within(form).getByLabelText('Alert rule name'), 'Sumy strikes');
    await chooseCountry(user, within(form), 'Ukraine');
    await user.click(within(form).getByRole('radio', { name: 'Specific categories' }));
    await user.click(within(form).getByRole('checkbox', { name: 'Conflict & unrest' }));
    await user.type(within(form).getByLabelText('Keywords'), 'Sumy, strike');
    await user.clear(within(form).getByLabelText('Threshold'));
    await user.type(within(form).getByLabelText('Threshold'), '3');
    await user.selectOptions(within(form).getByLabelText('Window'), '1440');
    await user.selectOptions(within(form).getByLabelText('Report when it fires'), 'intsum');
    await user.click(within(form).getByRole('button', { name: 'Add alert rule' }));
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

  it('is retired from navigation but still answers for anyone holding the link', async () => {
    renderApp('/settings', 'user');
    await screen.findByRole('heading', { name: 'Settings' });
    const page = within(screen.getByRole('main'));
    expect(page.queryByRole('link', { name: /^Alerts & rules/ })).toBeNull();
    const primary = within(screen.getByRole('navigation', { name: 'Primary' }));
    expect(primary.queryByRole('link', { name: 'Alerts & rules' })).toBeNull();
    expect(screen.queryByRole('link', { name: /unacknowledged/ })).not.toBeInTheDocument();
  });

  it('still lists the alerts it holds when the page is opened directly', async () => {
    renderApp('/warning', 'user');
    const list = await screen.findByRole('list', { name: 'Alerts' });
    expect(within(list).getAllByRole('listitem')).toHaveLength(2);
  });
});
