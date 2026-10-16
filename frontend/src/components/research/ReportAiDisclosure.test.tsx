import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { report } from '@/test/fixtures';
import { DailyBriefingSummary } from './DailyBriefingSummary';
import { ReportAiDisclosure } from './ReportAiDisclosure';
import { MemoryRouter } from 'react-router';

it('keeps an AI label on resumed generated reports even when no new attempt was needed', () => {
  const version = { ...report.version, attempts: 0, status: 'failed' as const };
  render(<ReportAiDisclosure version={version} />);
  expect(screen.getByText('AI-assisted assessment')).toBeVisible();
});

it('uses the explicit no-evidence marker in daily previews too', () => {
  const saved = structuredClone(report);
  saved.version.findings = [
    {
      rule: 'no_evidence',
      severity: 'error',
      location: 'evidence',
      message: 'No eligible evidence.',
    },
  ];
  render(
    <MemoryRouter>
      <DailyBriefingSummary report={saved} />
    </MemoryRouter>,
  );
  expect(screen.getByText(/No AI assessment was generated/)).toBeVisible();
  expect(screen.queryByText('AI-assisted assessment')).not.toBeInTheDocument();
});
