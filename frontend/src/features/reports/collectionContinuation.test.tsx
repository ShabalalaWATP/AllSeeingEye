import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it } from 'vitest';
import { researchReceiptSchema } from '@/lib/api/reportResearch';
import { researchReceipt } from '@/test/fixtures.researchMetadata';
import { ResearchCoverage } from './ResearchCoverage';

const trace = {
  policy_version: 'ase-collection-review-v1',
  decision: 'continue',
  requested_decision: 'sufficient',
  basis: 'question_addressed',
  rationale: 'The collected text appears to address the question.',
  citations: [
    {
      event_id: 'event-1',
      source_id: 'example',
      content_hash: 'hash-1',
      field: 'summary',
      quote: '<script>untrusted evidence</script>',
    },
  ],
  gaps: [],
  model: 'fixture-review-model',
  context_count: 1,
  total_count: 1,
  override_reason: 'An explicit operator search remains unfinished.',
};
const plan = {
  question: 'What happened?',
  since: researchReceipt.since,
  until: researchReceipt.until,
  languages: ['en'],
  mode: 'quick',
  focus: 'general',
  subject: null,
  country_iso: null,
  tasks: [],
  request_limit: 6,
  seconds_limit: 45,
  item_limit: 200,
  policy_version: 'ase-deterministic-plan-v1',
  model_calls: 1,
  translation_calls: 0,
  replans: 0,
};
it('shows the applied continuation separately from a denied model stop with exact inert excerpts', async () => {
  const receipt = researchReceiptSchema.parse({
    ...researchReceipt,
    plan: { ...plan, continuation: trace },
    passes: [{ terms: ['original'], attempts: [], plan }],
  });
  const { container } = render(<ResearchCoverage receipt={receipt} />);
  const user = userEvent.setup();
  await user.click(screen.getByText(/Collection coverage/));
  const review = within(screen.getByRole('region', { name: 'Collection continuation decision' }));
  expect(review.getByText('Keep the original search plan')).toBeVisible();
  expect(review.getByText(/Applied constraint: An explicit operator search/)).toBeVisible();
  expect(review.getByText(/not a guarantee of completeness or truth/)).toBeVisible();
  await user.click(review.getByText('Recorded review excerpts'));
  // This assertion checks escaped text; the next assertion rejects executable script nodes.
  // nosemgrep: javascript.lang.security.audit.unknown-value-with-script-tag.unknown-value-with-script-tag
  expect(review.getByText('<script>untrusted evidence</script>')).toBeVisible();
  expect(container.querySelector('script')).toBeNull();
  expect(review.getByText(/1 of 1 first-pass records/)).toBeVisible();
});

it('distinguishes a deliberate stop from failed or exhausted collection and leaves legacy reviews absent', () => {
  const receipt = researchReceiptSchema.parse({
    ...researchReceipt,
    plan: { ...plan, continuation: { ...trace, decision: 'sufficient', override_reason: null } },
    attempts: [
      {
        ...researchReceipt.attempts[0],
        status: 'not_collected',
        result_count: 0,
        explanation: 'Not requested after an applied sufficiency decision.',
      },
    ],
  });
  render(<ResearchCoverage receipt={receipt} />);
  expect(screen.getByText('Stop collection after the evidence review')).toBeInTheDocument();
  expect(screen.getByText(/not collected · 0 results/i)).toBeInTheDocument();
  expect(researchReceiptSchema.parse({ ...researchReceipt, plan }).plan?.continuation).toBeNull();
});

it('preserves a possible conflict as a model assessment with declared gaps', () => {
  render(
    <ResearchCoverage
      receipt={researchReceiptSchema.parse({
        ...researchReceipt,
        plan: {
          ...plan,
          continuation: {
            ...trace,
            decision: 'replan',
            requested_decision: 'replan',
            basis: 'potential_conflict',
            override_reason: null,
            gaps: ['The event date is unresolved.'],
          },
        },
      })}
    />,
  );
  expect(screen.getByText(/not a verified contradiction/)).toBeInTheDocument();
  expect(screen.getByText('The event date is unresolved.')).toBeInTheDocument();
  expect(screen.getByText('Run a revised search within the remaining budget')).toBeInTheDocument();
});
