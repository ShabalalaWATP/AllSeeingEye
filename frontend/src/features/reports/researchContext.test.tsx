import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { report } from '@/test/fixtures';
import { researchContext, reportChallenge } from '@/test/fixtures.researchContext';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { reportSchema } from '@/lib/api/reports';
import { ResearchContextView } from './ResearchContext';
import { ReportChallengeView } from './ReportChallenge';

describe('frozen context and challenge reader', () => {
  it('loads frozen context after the answer and distinguishes initial searches from all final reviews', async () => {
    server.use(
      http.get('/api/reports/:id', () =>
        HttpResponse.json({
          ...report,
          version: {
            ...report.version,
            research_context: researchContext,
            challenge: reportChallenge,
          },
        }),
      ),
    );
    const { user, container } = renderApp(`/reports/${report.report.id}`, 'user');
    const answer = await screen.findByRole('heading', { name: 'Executive summary' });
    await user.click(screen.getByRole('button', { name: 'Sources & methods' }));
    await user.click(await screen.findByRole('button', { name: 'Assessment' }));
    const disclosure = await screen.findByText('Timeline and source context');
    expect(answer).toBeInTheDocument();
    await user.click(disclosure);
    expect(screen.getByText('registry_snapshot')).toBeVisible();
    expect(screen.getByText('registered_date_raw')).toBeVisible();
    expect(screen.getByText('<script>Declared alias</script>')).toBeVisible();
    expect(container.querySelector('script')).toBeNull();
    const sourceLinks = screen.getAllByRole('link', { name: 'Open declared source link' });
    expect(sourceLinks).toHaveLength(1);
    expect(sourceLinks[0]).toHaveAttribute('href', 'https://example.test/source');
    expect(sourceLinks[0]).toHaveAttribute('rel', 'noopener noreferrer');
    await user.click(screen.getByText('Challenge to the judgements · 2 reviews'));
    expect(screen.getByText('Final judgement wording.')).toBeVisible();
    expect(screen.getByText('A second final judgement.')).toBeVisible();
    expect(screen.getByText(/Review service was unavailable/)).toBeVisible();
    await user.click(screen.getByText('KJ1 · attempted · 0 collected'));
    expect(screen.getByText('Initial judgement wording.')).toBeVisible();
    expect(screen.getByText(/QA feed · budget exhausted/)).toBeVisible();
    expect(screen.getByText(/Missing counterevidence does not confirm/)).toBeVisible();
    expect(screen.getByRole('link', { name: /Ask a follow-up question/ })).toHaveAttribute(
      'href',
      `/research?parent=${report.report.id}&parent_version=1`,
    );
  });

  it('keeps empty and legacy states explicit without reconstructing records', async () => {
    const user = userEvent.setup();
    const { rerender } = render(<ResearchContextView context={null} />);
    expect(screen.getByText(/not recorded for this version/)).toBeVisible();
    rerender(
      <ResearchContextView
        context={{
          ...researchContext,
          timeline: [],
          identity_candidates: [],
          source_chains: [],
          source_relationships: [],
        }}
      />,
    );
    await user.click(screen.getByText('Timeline and source context'));
    for (const message of [
      'No timeline entries recorded.',
      'No identity candidates recorded.',
      'No source links recorded.',
      'No relationship hints recorded.',
    ])
      expect(screen.getByText(message)).toBeVisible();
    rerender(<ReportChallengeView challenge={{ ...reportChallenge, searches: [], reviews: [] }} />);
    await user.click(screen.getByText('Challenge to the judgements · 0 reviews'));
    expect(screen.getByText('No final reviews recorded.')).toBeVisible();
    expect(screen.getByText('No challenge search records saved.')).toBeVisible();
  });

  it('accepts denied-budget receipts but rejects invented identity verification status', () => {
    const payload = {
      ...report,
      version: {
        ...report.version,
        challenge: {
          ...reportChallenge,
          searches: [{ ...reportChallenge.searches[0], status: 'budget_exhausted' }],
        },
        research_context: researchContext,
      },
    };
    expect(reportSchema.safeParse(payload).success).toBe(true);
    expect(
      reportSchema.safeParse({
        ...payload,
        version: {
          ...payload.version,
          research_context: {
            ...researchContext,
            identity_candidates: [
              { ...researchContext.identity_candidates[0], status: 'verified' },
            ],
          },
        },
      }).success,
    ).toBe(false);
  });

  it('retains separate publication, observation and capture dates without an inferred timestamp', async () => {
    const user = userEvent.setup();
    render(<ResearchContextView context={researchContext} />);
    await user.click(screen.getByText('Timeline and source context'));
    const timeline = screen.getByRole('region', { name: 'Publication timeline' });
    expect(within(timeline).getByText('1 Sept 2026, 00:00 UTC')).toBeVisible();
    expect(within(timeline).getByText('4 Sept 2026, 00:00 UTC')).toBeVisible();
    expect(within(timeline).getByText('Not recorded')).toBeVisible();
  });
});
