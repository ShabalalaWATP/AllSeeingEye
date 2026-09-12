import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { report } from '@/test/fixtures';
import { citationChecks, researchReceipt, sourceContext } from '@/test/fixtures.researchMetadata';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { reportSchema } from '@/lib/api/reports';
import { EvidenceAnnex } from './EvidenceAnnex';
import { ResearchCoverage } from './ResearchCoverage';
import { CitationCheckMethod, JudgementCitationChecks } from './CitationChecks';

describe('saved research metadata', () => {
  it('renders the answer before coverage and exposes saved checks without re-querying sources', async () => {
    let sourceRequests = 0;
    server.use(
      http.get('/api/sources', () => {
        sourceRequests++;
        return HttpResponse.json({ items: [sourceContext] });
      }),
      http.get('/api/reports/:id', () =>
        HttpResponse.json({
          ...report,
          version: {
            ...report.version,
            research: researchReceipt,
            citation_checks: citationChecks,
          },
        }),
      ),
    );
    const { user, container } = renderApp(`/reports/${report.report.id}`, 'user');
    const answer = await screen.findByRole('heading', { name: 'Executive summary' });
    await user.click(screen.getByRole('button', { name: 'Sources & methods' }));
    await user.click(await screen.findByRole('button', { name: 'Assessment' }));
    expect(answer).toBeInTheDocument();
    await user.click(screen.getByText('Citation excerpts · Review required'));
    expect(screen.getByText('Overnight shelling.', { selector: 'blockquote' })).toBeVisible();
    expect(screen.getByText(/not contradiction findings/)).toBeVisible();
    expect(screen.getByText('Claim values: 12')).toBeVisible();
    await user.click(screen.getByText('Exact excerpt provenance'));
    expect(screen.getByText('qa-excerpt-hash')).toBeVisible();
    expect(container.querySelector('blockquote')).toHaveTextContent('Overnight shelling.');
    await user.click(screen.getByRole('button', { name: 'Collection' }));
    const coverage = await screen.findByText(/Collection coverage · 4 source task outcomes/);
    await user.click(coverage);
    for (const state of ['Completed', 'Empty', 'Unavailable', 'Failed'])
      expect(screen.getByText(new RegExp(`${state} ·`, 'i'))).toBeVisible();
    expect(screen.getByText('en, fr')).toBeVisible();
    expect(screen.getByText('Ukraine, shelling')).toBeVisible();
    expect(screen.getByText(/do not establish absence of events/)).toBeVisible();
    expect(sourceRequests).toBe(0);
  });

  it('shows frozen rating basis and scalar provenance without converting values into markup', async () => {
    const user = userEvent.setup();
    const item = {
      ...report.version.evidence[0]!,
      source_rating: sourceContext.rating,
      attributes: [
        { key: 'count', value: 0 },
        { key: 'confirmed', value: false },
        { key: 'missing', value: null },
        { key: 'raw', value: '<img src=x onerror=alert(1)>' },
      ],
    };
    const { container } = render(<EvidenceAnnex evidence={[item]} findings={[]} status="ready" />);
    await user.click(screen.getByText(item.title));
    await user.click(screen.getByText(/Saved source rating basis/));
    expect(screen.getByText(/Frozen with this report version/)).toBeVisible();
    await user.click(screen.getByText('Retained source attributes'));
    expect(screen.getByText('0', { exact: true })).toBeVisible();
    expect(screen.getByText('false', { exact: true })).toBeVisible();
    expect(screen.getByText('Not recorded (null)')).toBeVisible();
    expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeVisible();
    expect(container.querySelector('img')).toBeNull();
  });

  it('retains legacy absence and rejects structurally invalid frozen metadata', () => {
    expect(reportSchema.safeParse(report).success).toBe(true);
    expect(
      reportSchema.safeParse({
        ...report,
        version: {
          ...report.version,
          research: {
            ...researchReceipt,
            attempts: [{ ...researchReceipt.attempts[0], status: 'verified' }],
          },
        },
      }).success,
    ).toBe(false);
    render(
      <>
        <ResearchCoverage receipt={null} />
        <CitationCheckMethod checks={undefined} />
      </>,
    );
    expect(screen.getByText(/Collection receipt not recorded/)).toBeVisible();
    expect(screen.getByText(/No checks have been recomputed/)).toBeVisible();
  });

  it('handles empty saved attempts and citation checks without inventing a positive result', async () => {
    const user = userEvent.setup();
    render(
      <>
        <ResearchCoverage receipt={{ ...researchReceipt, attempts: [] }} />
        <JudgementCitationChecks
          check={{ judgement_id: 'KJ-2', status: 'absent', reasons: [], citations: [] }}
        />
        <CitationCheckMethod checks={{ ...citationChecks, judgements: [] }} />
      </>,
    );
    await user.click(screen.getByText(/Collection coverage/));
    expect(screen.getByText('No collection attempts recorded.')).toBeVisible();
    await user.click(screen.getByText('Citation excerpts · Excerpt absent'));
    expect(screen.getByText('No citation checks recorded for this judgement.')).toBeVisible();
    await user.click(screen.getByText('Citation check method and limits'));
    expect(screen.getByText('No judgement citation checks recorded.')).toBeVisible();
  });

  it.each(['context_insufficient', 'excerpt_present'] as const)(
    'shows %s as an observation with reasons, not claim verification',
    async (status) => {
      const user = userEvent.setup();
      const check = {
        ...citationChecks.judgements[0]!,
        status,
        citations: [
          { ...citationChecks.judgements[0]!.citations[0]!, status, excerpt: null, indicators: [] },
        ],
      };
      render(<JudgementCitationChecks check={check} />);
      await user.click(screen.getByText(/Citation excerpts/));
      const region = screen.getByRole('region', { name: 'E1 supporting citation check' });
      expect(within(region).getByText(/Exact text is present/)).toBeVisible();
      expect(screen.queryByText('Exact excerpt provenance')).not.toBeInTheDocument();
    },
  );
});
