import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { schedule } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('schedules', () => {
  it('lists the standing orders with their cadence and last report', async () => {
    renderApp('/research/recurring', 'user');
    const table = await screen.findByRole('table', { name: 'Schedules' });
    expect(within(table).getByText('Morning INTSUM')).toBeInTheDocument();
    expect(within(table).getByText('daily at 06:00 UTC')).toBeInTheDocument();
    expect(within(table).getByText('intsum · UA')).toBeInTheDocument();
    expect(within(table).getByRole('link', { name: 'Report' })).toHaveAttribute(
      'href',
      `/reports/${schedule.last_report_id ?? ''}`,
    );
  });

  it('creates a weekly schedule from the form', async () => {
    let captured: unknown = null;
    server.use(
      http.post('/api/schedules', async ({ request }) => {
        captured = await request.json();
        return HttpResponse.json(schedule, { status: 201 });
      }),
    );
    const { user } = renderApp('/research/recurring', 'user');
    const form = await screen.findByRole('form', { name: 'New schedule' });
    await user.click(within(form).getByText('Advanced scope and sources'));
    await user.type(within(form).getByLabelText('Schedule name'), 'Monday roll-up');
    await user.selectOptions(within(form).getByLabelText('Product'), 'intsum');
    await user.click(within(form).getByText('Choose countries'));
    await user.click(within(form).getByRole('checkbox', { name: /^Ukraine/ }));
    await user.selectOptions(within(form).getByLabelText('Hour'), '7');
    await user.selectOptions(within(form).getByLabelText('Cadence'), 'weekly');
    await user.selectOptions(within(form).getByLabelText('Weekday'), '0');
    await user.click(within(form).getByRole('button', { name: 'Add schedule' }));
    await waitFor(() => {
      expect(captured).toEqual({
        name: 'Monday roll-up',
        notify_on_change: false,
        research_focus: 'general',
        research_web_search: false,
        enabled: true,
        template_id: 'intsum',
        country_iso: 'UA',
        country_isos: ['UA'],
        window_hours: 168,
        hour_utc: 7,
        cadence: 'weekly',
        weekday: 0,
        monthday: 1,
      });
    });
  });
});
