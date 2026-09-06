import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { report, reportSummary } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const analysed = {
  ...report,
  version: {
    ...report.version,
    direction: {
      pir: 'Will fighting around Kharkiv intensify this week?',
      sirs: ['Force posture'],
      eeis: ['Are reinforcements moving north?', 'Has the strike rate risen?'],
      search_terms: ['Kharkiv', 'drone'],
      categories: ['conflict'],
    },
    devils_advocacy: {
      target: 'KJ1',
      argument: 'The strikes fit routine harassment rather than preparation.',
      evidence: ['E2'],
      lower_confidence: true,
      rationale: 'Two items from one theatre.',
      confidence_before: 'moderate',
      confidence_after: 'low',
    },
  },
};

describe('direction, advocacy and archives in the reader', () => {
  it('shows the requirements, the contrarian view and archive links', async () => {
    server.use(http.get('/api/reports/:id', () => HttpResponse.json(analysed)));
    const { user } = renderApp(`/reports/${reportSummary.id}`, 'user');
    const direction = await screen.findByRole('region', { name: 'Direction' });
    expect(within(direction).getByText('PIR-1')).toBeInTheDocument();
    expect(within(direction).getByText('Has the strike rate risen?')).toBeInTheDocument();
    expect(within(direction).getByText('EEI-2')).toBeInTheDocument();
    expect(within(direction).getByText('Search terms: Kharkiv, drone')).toBeInTheDocument();

    const advocacy = screen.getByRole('region', { name: "Devil's advocacy" });
    expect(within(advocacy).getByText(/routine harassment/)).toBeInTheDocument();
    expect(
      within(advocacy).getByText(/Confidence on KJ1 lowered from moderate to low\./),
    ).toBeInTheDocument();

    const annex = screen.getByRole('region', { name: 'Evidence annex' });
    await user.click(within(annex).getByText('Shelling in Kharkiv'));
    const archives = within(annex).getAllByRole('link', { name: 'Open archive' });
    expect(archives).toHaveLength(1);
    expect(archives[0]).toHaveAttribute(
      'href',
      'https://web.archive.org/web/20260905000000/https://example.org/e1',
    );
  });

  it('leaves the sections out when a version has neither', async () => {
    renderApp(`/reports/${reportSummary.id}`, 'user');
    await screen.findByRole('heading', { name: 'Intelligence summary: Ukraine' });
    expect(screen.queryByRole('region', { name: 'Direction' })).not.toBeInTheDocument();
    expect(screen.queryByRole('region', { name: "Devil's advocacy" })).not.toBeInTheDocument();
  });

  it('sends the devil’s advocacy flag only when ticked', async () => {
    let body: Record<string, unknown> | null = null;
    server.use(
      http.post('/api/reports', async ({ request }) => {
        body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(report, { status: 201 });
      }),
    );
    const { user } = renderApp('/reports', 'user');
    const form = await screen.findByRole('form', { name: 'Generate a report' });
    await user.click(within(form).getByRole('checkbox', { name: /Devil's advocacy/ }));
    await user.click(within(form).getByRole('button', { name: 'Generate' }));
    await waitFor(() => {
      expect(body).toEqual({
        template: 'intsum',
        research_focus: 'general',
        report_language: 'en',
        report_style: 'assessment',
        devils_advocacy: true,
      });
    });
  });
});
