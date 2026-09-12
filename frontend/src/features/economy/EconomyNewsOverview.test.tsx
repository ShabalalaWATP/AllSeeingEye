import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { report } from '@/test/fixtures';
import { economyNews } from '@/test/fixtures.economy';
import { reportJob } from '@/test/reportJobFixture';
import type { EconomyBriefing } from '@/lib/api/economyBriefing';
import { EconomyNewsOverview } from './EconomyNewsOverview';

const briefing: EconomyBriefing = {
  job: reportJob(),
  window_days: 2,
  period_from: '2026-09-10T12:00:00Z',
  period_to: '2026-09-12T12:00:00Z',
  next_refresh_at: '2026-09-13T12:00:00Z',
  coverage_note: '',
};

it('shows the cited global takeaway with its reporting dates and review status', () => {
  render(
    <EconomyNewsOverview
      region="WORLD"
      items={[]}
      briefing={briefing}
      report={{ ...report, version: { ...report.version, status: 'needs_review' } }}
    />,
  );
  expect(screen.getByText(report.version.body.key_judgements[0]!.statement)).toBeVisible();
  expect(screen.getAllByRole('link').length).toBeGreaterThan(0);
  expect(screen.getByText(/From the 2-day briefing/)).toHaveTextContent(
    '10 Sept 2026, 12:00 UTC to 12 Sept 2026, 12:00 UTC',
  );
  expect(screen.getByText(/This assessment needs review/)).toBeVisible();
});

it('uses just the opening country paragraph and preserves its citations', () => {
  render(
    <EconomyNewsOverview
      region="US"
      items={[]}
      briefing={briefing}
      report={{
        ...report,
        version: {
          ...report.version,
          status: 'ready',
          body: {
            ...report.version.body,
            assessment: [
              {
                heading: 'U.S.',
                text: 'The opening economic takeaway.\n\nDetailed explanation retained in the full summary.',
                evidence: [report.version.evidence[0]!.label],
              },
            ],
          },
        },
      }}
    />,
  );
  expect(screen.getByText('The opening economic takeaway.')).toBeVisible();
  expect(screen.queryByText(/Detailed explanation/)).not.toBeInTheDocument();
  expect(screen.queryByText(/needs review/)).not.toBeInTheDocument();
  expect(screen.getByRole('link')).toHaveAttribute('href', report.version.evidence[0]!.url);
});

it('falls back to attributed reporting when a country assessment has no matched citation', () => {
  render(
    <EconomyNewsOverview
      region="CN"
      items={economyNews.items.slice(0, 1)}
      briefing={briefing}
      report={{
        ...report,
        version: {
          ...report.version,
          body: {
            ...report.version.body,
            assessment: [{ heading: 'China', text: 'Unbacked assessment.', evidence: ['missing'] }],
          },
        },
      }}
    />,
  );
  expect(screen.queryByText('Unbacked assessment.')).not.toBeInTheDocument();
  expect(screen.getByText(/The leading available reports/)).toHaveTextContent('Bank of England');
});

it('does not invent a summary for an empty source and report selection', () => {
  const { container } = render(
    <EconomyNewsOverview region="IR" items={[]} briefing={null} report={null} />,
  );
  expect(container).toBeEmptyDOMElement();
});
