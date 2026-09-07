import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { researchReceipt } from '@/test/fixtures.researchMetadata';
import { researchReceiptSchema } from '@/lib/api/reportResearch';
import { ResearchCoverage } from './ResearchCoverage';

it('keeps two outcomes for one source and labels retained candidates as hypotheses', () => {
  const candidate = { id: 'candidate-1', label: 'Acme UK', identifiers: ['UK 01234567'] };
  const task = {
    task_id: 'operator:identity',
    source_id: 'example',
    source_name: 'Example search',
    purpose: 'disambiguation',
    candidate_id: candidate.id,
    selected: true,
    supported: true,
    language: 'en',
    terms: ['Acme UK 01234567'],
    provenance: 'operator_supplied_task',
    temporal_scope: 'Recent records',
  };
  const receipt = researchReceiptSchema.parse({
    ...researchReceipt,
    plan: {
      question: 'Which Acme?',
      since: researchReceipt.since,
      until: researchReceipt.until,
      languages: ['en'],
      mode: 'quick',
      focus: 'general',
      subject: null,
      country_iso: null,
      tasks: [task],
      candidate_hypotheses: [candidate],
      request_limit: 6,
      seconds_limit: 45,
      item_limit: 200,
      policy_version: 'ase-deterministic-plan-v1',
      model_calls: 0,
      translation_calls: 0,
      replans: 0,
    },
    attempts: [
      {
        source_id: 'example',
        source_name: 'Example search',
        task_id: 'source:example',
        status: 'completed',
        result_count: 1,
        explanation: 'Baseline result',
        language: 'en',
      },
      {
        source_id: 'example',
        source_name: 'Example search',
        task_id: task.task_id,
        purpose: task.purpose,
        candidate_id: candidate.id,
        status: 'empty',
        result_count: 0,
        explanation: 'Identity search empty, identity unresolved',
        language: 'en',
      },
    ],
  });
  render(<ResearchCoverage receipt={receipt} />);
  expect(screen.getByText('Candidate hypotheses, not verified identities')).toBeInTheDocument();
  expect(screen.getByText(/Acme UK \(Operator-supplied\).*UK 01234567/)).toBeInTheDocument();
  expect(screen.getByText('Baseline result')).toBeInTheDocument();
  expect(screen.getByText('Identity search empty, identity unresolved')).toBeInTheDocument();
  expect(screen.getAllByText(/operator:identity/)).toHaveLength(2);
  expect(
    researchReceiptSchema.parse({
      ...researchReceipt,
      attempts: researchReceipt.attempts.map((attempt) => ({ ...attempt, purpose: undefined })),
    }).attempts[0]?.purpose,
  ).toBe('baseline');
});
