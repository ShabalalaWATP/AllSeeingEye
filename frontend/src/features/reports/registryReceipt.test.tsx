import { render, screen, within } from '@testing-library/react';
import { expect, it } from 'vitest';
import { researchReceiptSchema } from '@/lib/api/reportResearch';
import { ResearchCoverage } from './ResearchCoverage';
const lookup = {
  candidate_id: 'candidate',
  identifier_id: 'identifier',
  namespace: 'sec_cik' as const,
  original_value: '320193',
  subject: 'CIK:0000320193',
};
const base = {
  question: 'Which company?',
  since: '2026-09-01T00:00:00Z',
  until: '2026-09-02T00:00:00Z',
  languages: ['en'],
  mode: 'quick',
  focus: 'company',
  subject: 'Acme',
  country_iso: null,
  request_limit: 6,
  seconds_limit: 45,
  item_limit: 200,
  policy_version: 'test-plan',
  model_calls: 0,
  translation_calls: 0,
  replans: 0,
};

it('shows exact original and canonical lookup provenance in unsupported outcomes and history', () => {
  const attempt = {
    source_id: 'sec',
    source_name: 'SEC submissions',
    task_id: 'operator:check',
    purpose: 'disambiguation',
    candidate_id: 'candidate',
    language: null,
    registry_lookup: lookup,
    status: 'unsupported',
    result_count: 0,
    explanation: 'Country restriction excludes this registry.',
  };
  const receipt = researchReceiptSchema.parse({
    ...base,
    terms: [],
    collected_items: 0,
    attempts: [attempt],
    plan: {
      ...base,
      candidate_hypotheses: [
        {
          id: 'candidate',
          label: 'Acme candidate',
          identifiers: [],
          registry_identifiers: [{ id: 'identifier', namespace: 'sec_cik', value: '320193' }],
        },
      ],
      tasks: [
        {
          ...attempt,
          selected: true,
          supported: false,
          terms: [],
          provenance: 'operator_supplied_task',
          temporal_scope: 'Current records only.',
        },
      ],
    },
  });
  render(<ResearchCoverage receipt={receipt} />);
  const outcomes = screen.getByRole('region', { name: 'Latest source outcomes', hidden: true });
  expect(within(outcomes).getByText('CIK:0000320193')).toBeInTheDocument();
  expect(screen.getByText('Country restriction excludes this registry.')).toBeInTheDocument();
  expect(screen.getAllByText(/does not establish an identity match/)).toHaveLength(2);
});
