import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { expect, it } from 'vitest';
import type { Report } from '@/lib/api/reports';
import { report } from '@/test/fixtures';
import { reportAssessment } from '@/test/fixtures.reportAssessment';
import { DailyBriefingSummary } from './DailyBriefingSummary';

function show(value: Report = structuredClone(report), detailed = false) {
  return render(
    <MemoryRouter>
      <DailyBriefingSummary report={value} detailed={detailed} />
    </MemoryRouter>,
  );
}

it('shows saved likelihood and final confidence while separating support from contrary citations', () => {
  const value = structuredClone(report);
  value.version.assessment = structuredClone(reportAssessment);
  const judgement = value.version.body.key_judgements[0]!;
  judgement.confidence = 'high';
  judgement.supporting_evidence = ['E1'];
  judgement.contradicting_evidence = ['E2'];
  show(value);
  const context = within(screen.getByRole('region', { name: 'Confidence and likelihood for KJ1' }));
  expect(context.getByText('Assessed likelihood').nextElementSibling).toHaveTextContent(
    'highly likely',
  );
  expect(context.getByText('Analytical confidence').nextElementSibling).toHaveTextContent('low');
  expect(context.getByText(/Confidence rationale:/)).toHaveTextContent(
    judgement.confidence_statement,
  );
  const supporting = within(context.getByText('Supporting evidence'));
  expect(supporting.getByRole('link', { name: 'Daily briefing reference 1' })).toBeInTheDocument();
  expect(
    supporting.queryByRole('link', { name: 'Daily briefing reference 2' }),
  ).not.toBeInTheDocument();
  const contrary = within(context.getByText('Contrary evidence'));
  expect(contrary.getByRole('link', { name: 'Daily briefing reference 2' })).toBeInTheDocument();
  expect(
    contrary.queryByRole('link', { name: 'Daily briefing reference 1' }),
  ).not.toBeInTheDocument();
  expect(screen.getByText(/Likelihood uses the UK probability yardstick/)).toBeInTheDocument();
  expect(screen.queryByText(report.version.model)).not.toBeInTheDocument();
});

it('does not apply another judgement’s final confidence to a legacy judgement', () => {
  const value = structuredClone(report);
  value.version.assessment = structuredClone(reportAssessment);
  value.version.assessment.judgements[0]!.judgement_id = 'OTHER';
  show(value);
  expect(screen.getByText('Analytical confidence').nextElementSibling).toHaveTextContent(
    'moderate',
  );
});

it('retains unassessed source provenance alongside the saved two-axis evidence grade', async () => {
  const value = structuredClone(report);
  const source = value.version.evidence[0]!;
  source.grade = 'D6';
  source.grade_rationale = 'Platform observation with no author-specific reliability assessment.';
  source.source_rating = {
    policy_version: 'retained-policy',
    status: 'unassessed',
    assessed_grade: null,
    basis: 'No independently assessed publisher.',
    scope: 'Platform material.',
    limitations: [],
    provenance_role: 'platform',
    publisher_reliability_assessed: false,
    reviewed_at: null,
  };
  show(value);
  const user = userEvent.setup();
  await user.click(screen.getAllByRole('link', { name: 'Daily briefing reference 1' })[0]!);
  expect(screen.getByText('Saved evidence grade: D6')).toBeVisible();
  expect(screen.getByText(source.grade_rationale)).toBeVisible();
  expect(screen.getByText(/F and 6 mean there was not enough basis to judge/)).toBeVisible();
  await user.click(screen.getByText('Saved source rating basis · Unassessed'));
  expect(screen.getByText('No independently assessed publisher.')).toBeVisible();
  expect(screen.getByText('Publisher reliability assessed').nextElementSibling).toHaveTextContent(
    'No',
  );
  expect(screen.getByText('Source rating basis not recorded for this version.')).toBeVisible();
  expect(screen.getAllByRole('link', { name: 'Open source' })).toHaveLength(1);
  await user.click(screen.getByText('Sources cited in this summary (2)'));
  expect(screen.getByText('Saved evidence grade: D6')).not.toBeVisible();
});

it('does not invent missing legacy grades, rationale, likelihood or confidence', async () => {
  const value = structuredClone(report);
  value.version.evidence[0]!.grade = '';
  value.version.evidence[0]!.grade_rationale = '';
  const judgement = value.version.body.key_judgements[0]!;
  judgement.confidence = '';
  judgement.probability = '';
  judgement.confidence_statement = '';
  judgement.supporting_evidence = [];
  judgement.contradicting_evidence = ['E1'];
  show(value);
  const context = within(screen.getByRole('region', { name: 'Confidence and likelihood for KJ1' }));
  expect(context.getAllByText('Not recorded')).toHaveLength(2);
  expect(context.getByText(/Not recorded for this judgement/)).toBeInTheDocument();
  expect(context.queryByText('Supporting evidence')).not.toBeInTheDocument();
  await userEvent.setup().click(context.getByRole('link', { name: 'Daily briefing reference 1' }));
  expect(screen.getByText('Saved evidence grade: Not recorded')).toBeVisible();
  expect(screen.getByText('Grade rationale not recorded.')).toBeVisible();
});

it('keeps detailed analysis and watch conditions while retaining an assessment-only fallback', () => {
  const value = structuredClone(report);
  const { unmount } = show(value, true);
  expect(screen.getByRole('region', { name: 'Detailed assessment' })).toHaveTextContent(
    'Trajectory',
  );
  expect(screen.getByRole('region', { name: 'Developments to watch' })).toHaveTextContent(
    'Reinforcements on the northern road',
  );
  unmount();
  value.version.body.key_judgements = [];
  show(value);
  const overall = within(screen.getByRole('region', { name: 'Overall situation' }));
  expect(overall.getByText('The front is active.')).toBeInTheDocument();
  expect(overall.getByRole('link', { name: 'Daily briefing reference 1' })).toBeInTheDocument();
  expect(overall.queryByText('Analytical confidence')).not.toBeInTheDocument();
});

it('identifies missing saved citations rather than manufacturing a numbered reference', () => {
  const value = structuredClone(report);
  value.version.body.key_judgements[0]!.supporting_evidence = ['UNKNOWN'];
  value.version.body.key_judgements[0]!.contradicting_evidence = [];
  value.version.body.assessment = [];
  value.version.body.reporting = [];
  show(value);
  expect(screen.getByText(/Some references could not be matched/)).toBeInTheDocument();
  expect(screen.queryByRole('link', { name: /Daily briefing reference/ })).not.toBeInTheDocument();
  expect(screen.queryByText(/Sources cited in this summary/)).not.toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Read full briefing and export' })).toBeInTheDocument();
});
