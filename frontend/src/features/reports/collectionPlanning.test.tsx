import { render, screen, within } from '@testing-library/react';
import { expect, it } from 'vitest';
import { userEvent } from '@testing-library/user-event';
import { researchReceiptSchema } from '@/lib/api/reportResearch';
import { collectionPlanningSchema } from '@/lib/api/collectionPlanning';
import { researchReceipt } from '@/test/fixtures.researchMetadata';
import { CollectionPlanning } from '@/components/reports/CollectionPlanning';
import { ResearchCoverage } from './ResearchCoverage';
const planning = {
  policy_version: 'ase-model-plan-v1',
  status: 'applied',
  requested_model: 'configured-model',
  returned_model: 'returned-model',
  call_count: 1,
  reason: 'Add a bounded search for differing registration records.',
  proposed_candidates: [
    {
      id: 'candidate-a',
      label: '<script>Alternative company</script>',
      identifiers: ['REG-123'],
      origin: 'model',
    },
  ],
  proposed_tasks: [
    {
      id: 'task-a',
      source_id: 'public_registry',
      purpose: 'disambiguation',
      terms: ['REG-123 alternative'],
      candidate_id: 'candidate-a',
      origin: 'model',
    },
  ],
  accepted_candidate_ids: ['candidate-a'],
  accepted_task_ids: ['model:task-a'],
};
const plan = {
  question: 'Which organisation is referenced?',
  since: researchReceipt.since,
  until: researchReceipt.until,
  languages: ['en'],
  mode: 'quick',
  focus: 'company',
  subject: 'Example company',
  country_iso: null,
  request_limit: 6,
  seconds_limit: 45,
  item_limit: 200,
  policy_version: 'ase-deterministic-plan-v1',
  model_calls: 1,
  translation_calls: 0,
  replans: 0,
  candidate_hypotheses: [
    { id: 'operator-a', label: 'Operator candidate', identifiers: [] },
    ...planning.proposed_candidates,
  ],
  tasks: [
    {
      source_id: 'public_registry',
      task_id: 'model:task-a',
      purpose: 'disambiguation',
      candidate_id: 'candidate-a',
      source_name: 'Public registry',
      selected: true,
      supported: true,
      language: 'en',
      terms: ['REG-123 alternative'],
      provenance: 'model_proposed_task',
      temporal_scope: 'requested_window',
    },
  ],
};
it('records model planning separately from execution and preserves operator versus model provenance', async () => {
  const receipt = researchReceiptSchema.parse({
    ...researchReceipt,
    plan: { ...plan, planning },
    attempts: [
      {
        ...researchReceipt.attempts[0],
        source_id: 'public_registry',
        source_name: 'Public registry',
        task_id: 'model:task-a',
        purpose: 'disambiguation',
        status: 'budget_exhausted',
        result_count: 0,
        explanation: 'The shared budget was reached before this search.',
      },
    ],
  });
  const { container } = render(<ResearchCoverage receipt={receipt} />);
  const user = userEvent.setup();
  await user.click(screen.getByText(/Collection coverage/));
  const recorded = within(screen.getByRole('region', { name: 'Automatic collection planning' }));
  expect(recorded.getByText('Model proposals added to the collection plan')).toBeVisible();
  expect(recorded.getByText('Initial planning model calls').nextSibling).toHaveTextContent('1');
  expect(recorded.getByText(/Added tasks may still be skipped/)).toBeVisible();
  expect(recorded.getByText('Added to plan; see recorded task outcome')).toBeVisible();
  expect(screen.getByText(/budget exhausted.*0 results/i)).toBeVisible();
  expect(screen.getByText(/Model-proposed task terms, not verified evidence/)).toBeVisible();
  expect(screen.getByText(/Operator candidate.*Operator-supplied/)).toBeVisible();
  expect(container.querySelector('script')).toBeNull();
  expect(recorded.getByText('<script>Alternative company</script>')).toBeVisible();
});
it('shows rejected proposals without turning them into accepted tasks', () => {
  render(
    <CollectionPlanning
      value={collectionPlanningSchema.parse({
        ...planning,
        status: 'rejected',
        accepted_candidate_ids: [],
        accepted_task_ids: [],
        reason: 'A proposed task used an unselected source.',
      })}
    />,
  );
  expect(screen.getByText('Model proposals were not accepted into the plan')).toBeInTheDocument();
  expect(screen.getAllByText('Not added to plan')).toHaveLength(2);
  expect(screen.queryByText('Added to plan; see recorded task outcome')).not.toBeInTheDocument();
});
it.each(['unavailable', 'skipped', 'empty'])(
  'shows %s planning without inventing proposals or calls',
  (status) => {
    render(
      <CollectionPlanning
        value={collectionPlanningSchema.parse({
          ...planning,
          status,
          call_count: status === 'empty' ? 1 : 0,
          proposed_candidates: [],
          proposed_tasks: [],
          accepted_candidate_ids: [],
          accepted_task_ids: [],
          reason: 'No eligible additions.',
        })}
      />,
    );
    expect(
      screen.queryByRole('region', { name: 'Model search proposals' }),
    ).not.toBeInTheDocument();
    expect(screen.getByText('Initial planning model calls').nextSibling).toHaveTextContent(
      status === 'empty' ? '1' : '0',
    );
  },
);
it('keeps legacy receipts without a model planning claim', () => {
  const receipt = researchReceiptSchema.parse({ ...researchReceipt, plan });
  render(<ResearchCoverage receipt={receipt} />);
  expect(
    screen.queryByRole('region', { name: 'Automatic collection planning' }),
  ).not.toBeInTheDocument();
});
it('rejects oversized traces and unknown planning status', () => {
  expect(collectionPlanningSchema.safeParse({ ...planning, call_count: 2 }).success).toBe(false);
  expect(collectionPlanningSchema.safeParse({ ...planning, status: 'verified' }).success).toBe(
    false,
  );
  expect(
    collectionPlanningSchema.safeParse({
      ...planning,
      proposed_tasks: Array(9).fill(planning.proposed_tasks[0]),
    }).success,
  ).toBe(false);
});
