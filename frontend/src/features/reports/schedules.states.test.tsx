import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { schedule } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const failure = (message: string) =>
  HttpResponse.json({ error: { code: 'server_error', message } }, { status: 500 });

describe('schedule states', () => {
  it('shows the error and the empty state', async () => {
    server.use(http.get('/api/schedules', () => failure('Schedules boom')));
    renderApp('/research/recurring', 'user');
    expect(await screen.findByText('Schedules boom')).toBeInTheDocument();
    server.use(http.get('/api/schedules', () => HttpResponse.json({ items: [] })));
    renderApp('/research/recurring', 'user');
    expect(await screen.findByText('No standing orders yet.')).toBeInTheDocument();
  });

  it('describes weekday and weekly orders with their last outcome, and deletes one', async () => {
    let deleted: string | null = null;
    server.use(
      http.get('/api/schedules', () =>
        HttpResponse.json({
          items: [
            {
              ...schedule,
              id: 'e3e3e3e3-e3e3-4e3e-8e3e-e3e3e3e3e3e3',
              cadence: 'weekdays',
              hour_utc: 9,
              enabled: false,
              last_error: 'RuntimeError: boom',
              last_report_id: null,
            },
            {
              ...schedule,
              id: 'e4e4e4e4-e4e4-4e4e-8e4e-e4e4e4e4e4e4',
              cadence: 'weekly',
              weekday: 2,
              country_iso: null,
              country_isos: [],
              last_report_id: null,
            },
          ],
        }),
      ),
      http.delete('/api/schedules/:id', ({ params }) => {
        deleted = String(params.id);
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user } = renderApp('/research/recurring', 'user');
    const table = await screen.findByRole('table', { name: 'Schedules' });
    expect(within(table).getByText('weekdays at 09:00 UTC')).toBeInTheDocument();
    expect(within(table).getByText('Wednesday at 06:00 UTC')).toBeInTheDocument();
    expect(within(table).getByText('RuntimeError: boom')).toBeInTheDocument();
    expect(within(table).getByText('not yet')).toBeInTheDocument();
    expect(within(table).getByText('intsum')).toBeInTheDocument();
    await user.click(within(table).getAllByRole('button', { name: 'Delete' })[1]!);
    await waitFor(() => {
      expect(deleted).toBe('e4e4e4e4-e4e4-4e4e-8e4e-e4e4e4e4e4e4');
    });
  });

  it('creates a daily order for the whole world after trying weekly', async () => {
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
    await user.selectOptions(within(form).getByLabelText('Product'), 'intsum');
    await user.type(within(form).getByLabelText('Schedule name'), 'World morning');
    await user.selectOptions(within(form).getByLabelText('Cadence'), 'weekly');
    expect(within(form).getByLabelText('Weekday')).toBeInTheDocument();
    await user.selectOptions(within(form).getByLabelText('Cadence'), 'daily');
    expect(within(form).queryByLabelText('Weekday')).not.toBeInTheDocument();
    await user.click(within(form).getByRole('button', { name: 'Add schedule' }));
    await waitFor(() => {
      expect(captured).toEqual({
        name: 'World morning',
        notify_on_change: false,
        research_focus: 'general',
        research_web_search: false,
        enabled: true,
        template_id: 'intsum',
        country_iso: null,
        country_isos: [],
        window_hours: 168,
        hour_utc: 6,
        cadence: 'daily',
        weekday: 0,
        monthday: 1,
      });
    });
  });
});
