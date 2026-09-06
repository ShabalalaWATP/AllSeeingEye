import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { aoi, plan } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const failure = (message: string) =>
  HttpResponse.json({ error: { code: 'server_error', message } }, { status: 500 });

describe('direction form edges', () => {
  it('drops an unreadable box, switches kinds back, and surfaces creation errors', async () => {
    let captured: unknown = null;
    server.use(
      http.post('/api/direction/aois', async ({ request }) => {
        captured = await request.json();
        return failure('Area boom');
      }),
      http.post('/api/direction/plans', () => failure('Plan boom')),
      http.get('/api/direction/plans', () =>
        HttpResponse.json({ items: [{ ...plan, countries: [] }] }),
      ),
    );
    const { user } = renderApp('/direction', 'user');
    const plans = await screen.findByRole('list', { name: 'Collection plans' });
    expect(within(plans).getByText('1 PIR, 2 SIR')).toBeInTheDocument();
    const areaForm = screen.getByRole('form', { name: 'New area of interest' });
    await user.selectOptions(within(areaForm).getByLabelText('Kind'), 'countries');
    await user.selectOptions(within(areaForm).getByLabelText('Kind'), 'bbox');
    await user.type(within(areaForm).getByLabelText('Area name'), 'Broken box');
    await user.type(within(areaForm).getByLabelText('West, south, east, north'), '1, 2');
    await user.click(within(areaForm).getByRole('button', { name: 'Add area' }));
    await waitFor(() => {
      expect(captured).toEqual({ name: 'Broken box', description: '', kind: 'bbox' });
    });
    expect(await screen.findByText('Area boom')).toBeInTheDocument();
    const planForm = screen.getByRole('form', { name: 'New collection plan' });
    await user.type(within(planForm).getByLabelText('Plan name'), 'Failing');
    await user.type(within(planForm).getByLabelText('Priority intelligence requirement'), 'Q?');
    await user.type(within(planForm).getByLabelText('Specific requirements'), 'Anything');
    await user.click(within(planForm).getByRole('button', { name: 'Add plan' }));
    expect(await screen.findByText('Plan boom')).toBeInTheDocument();
    expect(screen.getAllByText(aoi.name).length).toBeGreaterThan(0);
  });
});
