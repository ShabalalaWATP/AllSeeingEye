import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { aoi, plan, planEvidence } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const failure = (message: string) =>
  HttpResponse.json({ error: { code: 'server_error', message } }, { status: 500 });

describe('direction states', () => {
  it('shows errors, empty lists and nation areas', async () => {
    server.use(
      http.get('/api/direction/aois', () => failure('Areas boom')),
      http.get('/api/direction/plans', () => HttpResponse.json({ items: [] })),
    );
    renderApp('/direction', 'user');
    expect(await screen.findByText('Areas boom')).toBeInTheDocument();
    expect(await screen.findByText('No plans yet.')).toBeInTheDocument();
    server.use(
      http.get('/api/direction/aois', () =>
        HttpResponse.json({
          items: [{ ...aoi, kind: 'countries', bbox: null, countries: ['UA', 'GB'] }],
        }),
      ),
      http.get('/api/direction/plans', () => failure('Plans boom')),
    );
    renderApp('/direction', 'user');
    expect(await screen.findByText('nations UA, GB')).toBeInTheDocument();
    expect(await screen.findByText('Plans boom')).toBeInTheDocument();
  });

  it('creates a nation area, deletes an area and scopes a plan to an area', async () => {
    let created: unknown = null;
    let deleted: string | null = null;
    let planBody: unknown = null;
    server.use(
      http.post('/api/direction/aois', async ({ request }) => {
        created = await request.json();
        return HttpResponse.json(aoi, { status: 201 });
      }),
      http.delete('/api/direction/aois/:id', ({ params }) => {
        deleted = String(params.id);
        return new HttpResponse(null, { status: 204 });
      }),
      http.post('/api/direction/plans', async ({ request }) => {
        planBody = await request.json();
        return HttpResponse.json(plan, { status: 201 });
      }),
    );
    const { user } = renderApp('/direction', 'user');
    const areaForm = await screen.findByRole('form', { name: 'New area of interest' });
    await user.type(within(areaForm).getByLabelText('Area name'), 'Two nations');
    await user.selectOptions(within(areaForm).getByLabelText('Kind'), 'countries');
    await user.type(within(areaForm).getByLabelText('Nations'), 'ua, gb');
    await user.click(within(areaForm).getByRole('button', { name: 'Add area' }));
    await waitFor(() => {
      expect(created).toEqual({
        name: 'Two nations',
        description: '',
        kind: 'countries',
        countries: ['UA', 'GB'],
      });
    });
    const table = screen.getByRole('table', { name: 'Areas of interest' });
    await user.click(within(table).getByRole('button', { name: 'Delete' }));
    await waitFor(() => {
      expect(deleted).toBe(aoi.id);
    });
    const planForm = screen.getByRole('form', { name: 'New collection plan' });
    await user.type(within(planForm).getByLabelText('Plan name'), 'Scoped');
    await user.selectOptions(within(planForm).getByLabelText('Area'), aoi.id);
    await user.type(within(planForm).getByLabelText('Priority intelligence requirement'), 'Q?');
    await user.type(within(planForm).getByLabelText('Specific requirements'), 'Anything');
    await user.type(within(planForm).getByLabelText('Background'), 'Context');
    await user.click(within(planForm).getByRole('button', { name: 'Add plan' }));
    await waitFor(() => {
      expect(planBody).toMatchObject({ name: 'Scoped', aoi_id: aoi.id, description: 'Context' });
    });
  });

  it('reports a missing plan and renders a bare one', async () => {
    renderApp('/direction/plans/00000000-0000-4000-8000-000000000000', 'user');
    expect(await screen.findByText('Plan not found.')).toBeInTheDocument();
    server.use(
      http.get('/api/direction/plans/:id', () =>
        HttpResponse.json({
          ...planEvidence,
          aoi: null,
          considered: 0,
          sirs: [],
          plan: {
            ...plan,
            description: '',
            countries: [],
            aoi_id: null,
            pirs: [
              {
                code: 'PIR-1',
                text: 'Bare question',
                sirs: [{ code: 'SIR-1.1', text: 'Bare', keywords: [], categories: [] }],
              },
            ],
          },
        }),
      ),
    );
    renderApp(`/direction/plans/${plan.id}`, 'user');
    expect(await screen.findByText(/no area/)).toBeInTheDocument();
    expect(screen.getByText('no keywords')).toBeInTheDocument();
    expect(screen.getByText('Nothing gathered in the last week.')).toBeInTheDocument();
  });
});
