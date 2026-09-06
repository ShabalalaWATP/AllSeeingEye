import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { report, reportSummary } from '@/test/fixtures';
import { reportAssessment } from '@/test/fixtures.reportAssessment';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

function serveAssessment(assessment: unknown = reportAssessment) {
  server.use(
    http.get('/api/reports/:id', () =>
      HttpResponse.json({
        ...report,
        version: { ...report.version, assessment },
      }),
    ),
  );
}

describe('saved report evidence assessment', () => {
  it('displays saved judgement counts, ceiling and final confidence without recalculating', async () => {
    serveAssessment();
    const { user } = renderApp(`/reports/${reportSummary.id}`, 'user');
    const summary = await screen.findByRole('region', { name: 'Evidence strength' });
    expect(within(summary).getByText('Supported judgements').nextElementSibling).toHaveTextContent(
      '0',
    );
    expect(within(summary).getByText('Contested judgements').nextElementSibling).toHaveTextContent(
      '1',
    );
    expect(within(summary).getByText(/Validation:/)).toHaveTextContent('0 errors · 1 warnings');
    expect(within(summary).getByText(/2 evidence items/)).toHaveTextContent(
      '1 declared organisation group',
    );
    expect(within(summary).getByText(/Grades and supporting/)).toHaveTextContent(
      'remain unverified',
    );
    const rating = screen.getByRole('region', { name: 'Evidence assessment for KJ1' });
    expect(within(rating).getByText('Confidence ceiling').nextElementSibling).toHaveTextContent(
      'moderate',
    );
    expect(within(rating).getByText('Final confidence').nextElementSibling).toHaveTextContent(
      'low',
    );
    await user.click(within(rating).getByText('Why this evidence rating?'));
    expect(within(rating).getByText('Supporting strength:')).toHaveTextContent('strong');
    expect(within(rating).getByText('Opposing strength:')).toHaveTextContent('limited');
    expect(within(rating).getByText(/Seek separately/)).toBeVisible();
    expect(within(rating).getByText(/Unavailable citations:/)).toHaveTextContent('E9');
    expect(
      within(rating).queryByRole('link', { name: 'View evidence E9' }),
    ).not.toBeInTheDocument();
    const citation = within(rating).getAllByRole('link', { name: 'View evidence E1' })[0]!;
    citation.focus();
    await user.keyboard('{Enter}');
    expect(screen.getByText('Shelling in Kharkiv').closest('summary')).toHaveFocus();
    expect(screen.getByText('B2 permits a strong contribution.')).toBeVisible();
  });

  it.each([undefined, null])(
    'keeps an absent legacy assessment unavailable (%s)',
    async (assessment) => {
      // Explicitly omit the property as well as testing the nullable API representation.
      server.use(
        http.get('/api/reports/:id', () =>
          HttpResponse.json({
            ...report,
            version: { ...report.version, assessment },
          }),
        ),
      );
      renderApp(`/reports/${reportSummary.id}`, 'user');
      expect(
        await screen.findByText(/Assessment not recorded for this version/),
      ).toBeInTheDocument();
      expect(screen.queryByText('Supported judgements')).not.toBeInTheDocument();
      expect(
        screen.queryByRole('region', { name: 'Evidence assessment for KJ1' }),
      ).not.toBeInTheDocument();
    },
  );

  it('explains an assessment with no key judgements', async () => {
    serveAssessment({
      ...reportAssessment,
      judgements: [],
      tallies: {
        ...reportAssessment.tallies,
        judgements: 0,
        supported_judgements: 0,
        contested_judgements: 0,
      },
    });
    renderApp(`/reports/${reportSummary.id}`, 'user');
    expect(
      await screen.findByText('No key judgements were recorded for assessment.'),
    ).toBeInTheDocument();
  });

  it('does not silently present malformed new assessments as legacy data', async () => {
    serveAssessment({
      ...reportAssessment,
      judgements: [{ ...reportAssessment.judgements[0], support_tier: 'certain' }],
    });
    renderApp(`/reports/${reportSummary.id}`, 'user');
    expect(await screen.findByRole('alert')).toHaveTextContent(/invalid|unexpected|match/i);
    expect(screen.queryByText(/Assessment not recorded/)).not.toBeInTheDocument();
  });
});
