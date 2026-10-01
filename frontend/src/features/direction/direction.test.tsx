import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { aoi, plan } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('direction', () => {
  it('lists areas and plans, and creates an area from the form', async () => {
    let captured: unknown = null;
    server.use(
      http.post('/api/direction/aois', async ({ request }) => {
        captured = await request.json();
        return HttpResponse.json(aoi, { status: 201 });
      }),
    );
    const { user } = renderApp('/direction', 'user');
    const areas = await screen.findByRole('table', { name: 'Areas of interest' });
    expect(within(areas).getByText('Eastern Ukraine')).toBeInTheDocument();
    expect(within(areas).getByText('box 30.0, 44.0, 41.0, 53.0')).toBeInTheDocument();
    const plans = screen.getByRole('list', { name: 'Collection plans' });
    expect(within(plans).getByRole('link', { name: 'Kharkiv axis' })).toHaveAttribute(
      'href',
      `/direction/plans/${plan.id}`,
    );
    expect(within(plans).getByText('1 PIR, 2 SIR · UA')).toBeInTheDocument();

    const form = screen.getByRole('form', { name: 'New area of interest' });
    await user.type(within(form).getByLabelText('Area name'), 'Kharkiv box');
    await user.type(within(form).getByLabelText('West, south, east, north'), '35, 48, 38, 51');
    await user.click(within(form).getByRole('button', { name: 'Add area' }));
    await waitFor(() => {
      expect(captured).toEqual({
        name: 'Kharkiv box',
        description: '',
        kind: 'bbox',
        bbox: [35, 48, 38, 51],
      });
    });
  });

  it('shows a plan with the evidence per requirement, and deletes it', async () => {
    const { user } = renderApp(`/direction/plans/${plan.id}`, 'user');
    expect(await screen.findByRole('heading', { name: 'Kharkiv axis' })).toBeInTheDocument();
    expect(screen.getByText('Background from the curated tracker.')).toBeInTheDocument();
    expect(screen.getByText(/Eastern Ukraine \(box/)).toBeInTheDocument();
    const pir = screen.getByRole('region', { name: 'PIR-1' });
    expect(within(pir).getByText('Shelling in Kharkiv')).toBeInTheDocument();
    expect(within(pir).getByText('keywords: Kharkiv, shelling')).toBeInTheDocument();
    expect(within(pir).getByText('Nothing gathered in the last week.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Generate assessment' })).toHaveAttribute(
      'href',
      `/research?brief=new&plan=${plan.id}`,
    );
    await user.click(screen.getByRole('button', { name: 'Delete plan' }));
    expect(await screen.findByRole('heading', { name: 'Plans and areas' })).toBeInTheDocument();
  });
});
