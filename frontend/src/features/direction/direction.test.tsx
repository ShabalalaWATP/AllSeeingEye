import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { aoi, plan, report, reportSummary } from '@/test/fixtures';
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

  it('creates a plan from the compact requirement lines', async () => {
    let captured: unknown = null;
    server.use(
      http.post('/api/direction/plans', async ({ request }) => {
        captured = await request.json();
        return HttpResponse.json(plan, { status: 201 });
      }),
    );
    const { user } = renderApp('/direction', 'user');
    const form = await screen.findByRole('form', { name: 'New collection plan' });
    await user.type(within(form).getByLabelText('Plan name'), 'Sumy watch');
    await user.type(within(form).getByLabelText('Nations'), 'ua, xx1');
    await user.type(
      within(form).getByLabelText('Priority intelligence requirement'),
      'Is Sumy next?',
    );
    await user.type(
      within(form).getByLabelText('Specific requirements'),
      'Strikes near Sumy | Sumy, strike | conflict{enter}Talks | talks | news, bogus{enter}',
    );
    await user.click(within(form).getByRole('button', { name: 'Add plan' }));
    await waitFor(() => {
      expect(captured).toEqual({
        name: 'Sumy watch',
        enabled: true,
        description: '',
        aoi_id: null,
        countries: ['UA'],
        pirs: [
          {
            text: 'Is Sumy next?',
            sirs: [
              { text: 'Strikes near Sumy', keywords: ['Sumy', 'strike'], categories: ['conflict'] },
              { text: 'Talks', keywords: ['talks'], categories: ['news'] },
            ],
          },
        ],
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
      `/reports?template=ask&plan=${plan.id}`,
    );
    await user.click(screen.getByRole('button', { name: 'Delete plan' }));
    expect(await screen.findByRole('heading', { name: 'Direction' })).toBeInTheDocument();
  });

  it('generates a plan-scoped ask without typing a question', async () => {
    let captured: unknown = null;
    server.use(
      http.post('/api/reports', async ({ request }) => {
        captured = await request.json();
        return HttpResponse.json(
          { ...report, report: { ...reportSummary, id: '99999999-9999-4999-8999-999999999999' } },
          { status: 201 },
        );
      }),
    );
    const { user } = renderApp(`/reports?template=ask&plan=${plan.id}`, 'user');
    const form = await screen.findByRole('form', { name: 'Generate a report' });
    expect(within(form).getByText(/Scoped by a collection plan/)).toBeInTheDocument();
    expect(within(form).getByLabelText('Question')).not.toBeRequired();
    await user.click(within(form).getByRole('button', { name: 'Generate' }));
    await waitFor(() => {
      expect(captured).toEqual({
        disclose_area_to_provider: false,
        template: 'ask',
        plan: plan.id,
        research_focus: 'general',
        report_language: 'en',
        report_style: 'assessment',
        devils_advocacy: false,
      });
    });
  });
});
