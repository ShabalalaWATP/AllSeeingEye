import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { expect, it } from 'vitest';
import type { Report } from '@/lib/api/reports';
import { report } from '@/test/fixtures';
import { reportAssessment } from '@/test/fixtures.reportAssessment';
import { IntelligenceSummary } from './IntelligenceSummary';

function show(value = structuredClone(report), subject = 'Cyber') {
  return render(
    <MemoryRouter>
      <IntelligenceSummary report={value} subject={subject} />
    </MemoryRouter>,
  );
}

it.each(['Cyber', 'Economic'])(
  'retains distinct likelihood, final confidence and rationale in %s summaries',
  async (subject) => {
    const value = structuredClone(report);
    value.version.assessment = structuredClone(reportAssessment);
    value.version.body.key_judgements[0]!.confidence = 'high';
    value.version.body.key_judgements[0]!.supporting_evidence = ['E1'];
    value.version.body.key_judgements[0]!.contradicting_evidence = ['E2'];
    show(value, subject);
    const judgement = within(
      screen.getByRole('region', { name: 'Confidence and likelihood for KJ1' }),
    );
    expect(judgement.getByText('Assessed likelihood').nextElementSibling).toHaveTextContent(
      'highly likely',
    );
    expect(judgement.getByText('Analytical confidence').nextElementSibling).toHaveTextContent(
      'low',
    );
    expect(judgement.getByText(/Confidence rationale:/).closest('p')).toHaveTextContent(
      'Two independent organisations; volatile front.',
    );
    expect(judgement.getByText('Supporting evidence cited')).toHaveTextContent('[1]');
    expect(judgement.getByText('Contrary evidence cited')).toHaveTextContent('[2]');
    await userEvent.setup().click(judgement.getByText('Evidence review'));
    expect(judgement.getByText(/Recorded confidence ceiling/)).toHaveTextContent('moderate');
    expect(
      judgement.getByText('A strong supporting group outweighs limited opposing evidence.'),
    ).toBeVisible();
    expect(screen.queryByText(value.version.model)).not.toBeInTheDocument();
  },
);

it('uses the saved judgement confidence when an older report has no engine assessment', () => {
  show();
  const judgement = within(
    screen.getByRole('region', { name: 'Confidence and likelihood for KJ1' }),
  );
  expect(judgement.getByText('Analytical confidence').nextElementSibling).toHaveTextContent(
    'moderate',
  );
  expect(judgement.queryByText('Evidence review')).not.toBeInTheDocument();
});

it('removes only a known repeated confidence preface when its saved review remains available', () => {
  const value = structuredClone(report);
  value.version.assessment = structuredClone(reportAssessment);
  const original =
    'Engine confidence ceiling: low. Model rationale (unverified): Coverage is limited.';
  value.version.body.key_judgements[0]!.confidence_statement = original;
  const { unmount } = show(value);
  expect(screen.getByText(/Confidence rationale:/).closest('p')).toHaveTextContent(
    'Coverage is limited.',
  );
  expect(screen.queryByText(/Engine confidence ceiling:/)).not.toBeInTheDocument();
  unmount();
  value.version.assessment = null;
  show(value);
  expect(screen.getByText(/Confidence rationale:/).closest('p')).toHaveTextContent(original);
});

it('keeps separate judgement metadata when duplicate text is displayed once', () => {
  const value = structuredClone(report);
  const original = value.version.body.key_judgements[0]!;
  value.version.body.key_judgements.push({
    ...original,
    id: 'KJ2',
    probability: 'realistic_possibility',
    confidence: 'low',
    confidence_statement: 'A second recorded judgement has a different basis.',
    supporting_evidence: [],
    contradicting_evidence: ['E2'],
  });
  value.version.body.assessment = [
    { heading: 'Repeated claim', text: original.statement, evidence: ['E1'] },
  ];
  show(value);
  expect(screen.getAllByText(original.statement)).toHaveLength(1);
  const second = within(screen.getByRole('region', { name: 'Confidence and likelihood for KJ2' }));
  expect(second.getByText('Assessed likelihood').nextElementSibling).toHaveTextContent(
    'realistic possibility',
  );
  expect(second.getByText('Analytical confidence').nextElementSibling).toHaveTextContent('low');
  expect(second.queryByText('Supporting evidence cited')).not.toBeInTheDocument();
  expect(second.getByText(/A second recorded judgement/)).toBeInTheDocument();
});

it('does not invent metadata for assessment prose or absent legacy values', () => {
  const value = structuredClone(report);
  value.version.body.key_judgements = [];
  const { unmount } = show(value);
  expect(screen.queryByText('Analytical confidence')).not.toBeInTheDocument();
  unmount();
  const missing = structuredClone(report);
  missing.version.body.key_judgements[0]!.probability = '';
  missing.version.body.key_judgements[0]!.confidence = '';
  missing.version.body.key_judgements[0]!.confidence_statement = '';
  show(missing);
  const judgement = within(
    screen.getByRole('region', { name: 'Confidence and likelihood for KJ1' }),
  );
  expect(judgement.getAllByText('Not recorded')).toHaveLength(2);
  expect(judgement.getByText(/Not recorded for this judgement/)).toBeInTheDocument();
});

it('explains the saved two-axis grade and preserves an unassessed source rating basis', async () => {
  const value: Report = structuredClone(report);
  const source = value.version.evidence[0]!;
  source.grade = 'D6';
  source.grade_rationale = 'A platform observation whose author is not independently assessed.';
  source.source_rating = {
    policy_version: 'retained-policy',
    status: 'unassessed',
    assessed_grade: null,
    basis: 'No source-specific reliability assessment.',
    scope: 'Individual platform authors.',
    limitations: ['The platform does not establish author reliability.'],
    provenance_role: 'platform',
    publisher_reliability_assessed: false,
    reviewed_at: null,
  };
  show(value);
  const user = userEvent.setup();
  await user.click(screen.getAllByRole('link', { name: 'Daily briefing reference 1' })[0]!);
  expect(screen.getByText('Saved evidence grade: D6')).toBeVisible();
  expect(
    screen.getByText(
      'Grade key: D = source not usually reliable; 6 = information cannot be judged.',
    ),
  ).toBeVisible();
  await user.click(screen.getByText('Saved source rating basis · Unassessed'));
  expect(screen.getByText('No source-specific reliability assessment.')).toBeVisible();
  expect(screen.getByText('Publisher reliability assessed').nextElementSibling).toHaveTextContent(
    'No',
  );
  expect(screen.getByText('Source rating basis not recorded for this version.')).toBeVisible();
});

it.each([
  ['F6', 'Grade key: F = source reliability cannot be judged; 6 = information cannot be judged.'],
  ['B2', 'Grade key: B = source usually reliable; 2 = information probably true.'],
  ['Q9', 'The recorded grade has no recognised scale description.'],
  ['', 'Grade rationale not recorded.'],
])('does not convert evidence grade %s into a truth percentage', async (grade, description) => {
  const value = structuredClone(report);
  value.version.evidence[0]!.grade = grade;
  value.version.evidence[0]!.grade_rationale = '';
  show(value);
  await userEvent
    .setup()
    .click(screen.getAllByRole('link', { name: 'Daily briefing reference 1' })[0]!);
  expect(screen.getByText(description)).toBeVisible();
  expect(screen.getByText(`Saved evidence grade: ${grade || 'Not recorded'}`)).toBeVisible();
  expect(screen.queryByText(/\d+%/)).not.toBeInTheDocument();
});

it('provides a concise doctrine guide with official links and separates probability from confidence', async () => {
  show();
  await userEvent
    .setup()
    .click(screen.getByText('Understanding likelihood, confidence and source grades'));
  expect(screen.getByText(/A highly likely judgement can still/)).toBeVisible();
  expect(screen.getByText(/F and 6 mean there is not enough basis to judge/)).toBeVisible();
  expect(screen.getByText(/not an official NATO scoring algorithm/)).toBeVisible();
  expect(
    screen.getByRole('link', { name: 'UK probability yardstick and confidence guidance' }),
  ).toHaveAttribute(
    'href',
    'https://www.gov.uk/government/publications/explaining-uncertainty-in-uk-intelligence-assessment/explaining-uncertainty-in-uk-intelligence-assessment',
  );
  expect(
    screen.getByRole('link', { name: 'UK MOD intelligence doctrine (JDP 2-00)' }),
  ).toHaveAttribute('rel', 'noopener noreferrer');
});
