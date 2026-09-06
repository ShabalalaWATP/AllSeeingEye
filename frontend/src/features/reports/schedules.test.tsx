import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { schedule } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('schedules', () => {
  it('lists the standing orders with their cadence and last report', async () => {
    renderApp('/reports', 'user');
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
    const { user } = renderApp('/reports', 'user');
    const form = await screen.findByRole('form', { name: 'New schedule' });
    await user.type(within(form).getByLabelText('Schedule name'), 'Monday roll-up');
    await user.selectOptions(within(form).getByLabelText('Product'), 'intsum');
    await user.selectOptions(within(form).getByLabelText('Nation'), 'UA');
    await user.selectOptions(within(form).getByLabelText('Hour'), '7');
    await user.selectOptions(within(form).getByLabelText('Cadence'), 'weekly');
    await user.selectOptions(within(form).getByLabelText('Weekday'), '0');
    await user.click(within(form).getByRole('button', { name: 'Add schedule' }));
    await waitFor(() => {
      expect(captured).toEqual({
        name: 'Monday roll-up',
        notify_on_change: false,
        research_focus: 'general',
        enabled: true,
        template_id: 'intsum',
        country_iso: 'UA',
        hour_utc: 7,
        cadence: 'weekly',
        weekday: 0,
      });
    });
  });
});
