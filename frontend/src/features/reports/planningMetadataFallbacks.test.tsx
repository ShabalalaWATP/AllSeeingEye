import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { CollectionPlanning } from '@/components/reports/CollectionPlanning';
import { SavedCollectionPlan } from '@/components/reports/SavedCollectionPlan';
import { planSchema } from '@/lib/api/researchPlan';
import type { CollectionPlanningTrace } from '@/lib/api/collectionPlanning';
const minimal = {
  question: 'What is known?',
  since: '2026-09-01T00:00:00Z',
  until: '2026-09-02T00:00:00Z',
  languages: [],
  mode: 'quick',
  focus: 'general',
  subject: null,
  country_iso: null,
  tasks: [],
  request_limit: 6,
  seconds_limit: 45,
  item_limit: 200,
  policy_version: 'legacy-plan',
  model_calls: 0,
  translation_calls: 0,
  replans: 0,
};
it('does not invent model names or distinguishing identifiers when planning metadata is absent', () => {
  const trace: CollectionPlanningTrace = {
    policy_version: 'ase-model-plan-v1',
    status: 'rejected',
    requested_model: '',
    returned_model: '',
    call_count: 1,
    reason: 'The source was not selected.',
    accepted_candidate_ids: [],
    accepted_task_ids: [],
    proposed_candidates: [
      { origin: 'model', id: 'empty', label: 'Candidate without identifiers', identifiers: [] },
      { origin: 'model', id: 'omitted', label: 'Legacy candidate' },
    ],
    proposed_tasks: [
      {
        origin: 'model',
        id: 'challenge',
        source_id: 'news',
        purpose: 'challenge',
        terms: ['Alternative account'],
      },
    ],
  };
  render(<CollectionPlanning value={trace} />);
  expect(screen.getAllByText('Not recorded')).toHaveLength(2);
  expect(screen.getAllByText('No distinguishing identifiers proposed')).toHaveLength(2);
  expect(screen.getByText(/Look for conflicting evidence/)).toBeInTheDocument();
  expect(screen.queryByText(/Candidate hypothesis:/)).not.toBeInTheDocument();
});
it('makes missing translation inputs and unavailable sources explicit in historical receipts', () => {
  render(
    <SavedCollectionPlan
      plan={planSchema.parse({
        ...minimal,
        translation: {
          policy_version: 'translation-v1',
          status: 'unavailable',
          model: '',
          languages: [],
          original_terms: [],
          variants: [],
        },
        area: { geometry: { type: 'Point', coordinates: [0, 0] }, sha256: 'a'.repeat(64) },
        tasks: [
          {
            source_id: 'legacy',
            source_name: 'Historical source',
            selected: false,
            supported: false,
            language: null,
            terms: [],
            purpose: 'challenge',
            provenance: 'legacy_import',
            temporal_scope: 'Unknown dates',
            spatial_supported: false,
            spatial_scope: 'No geometry support',
          },
        ],
      })}
    />,
  );
  expect(screen.getByText('None recorded')).toBeInTheDocument();
  expect(screen.getByText('No original phrases recorded.')).toBeInTheDocument();
  expect(screen.getByText('No translated phrases recorded.')).toBeInTheDocument();
  expect(screen.getByText(/Historical source.*Language-independent.*Excluded/)).toBeInTheDocument();
  expect(screen.getByText('No search terms recorded')).toBeInTheDocument();
  expect(screen.getByText(/Recorded provenance: legacy_import/)).toBeInTheDocument();
  expect(screen.getByText(/Area query unsupported: No geometry support/)).toBeInTheDocument();
});
it('retains a missing candidate reference and distinguishes replanned terms from operator variants', () => {
  const parsed = planSchema.parse({
    ...minimal,
    tasks: [
      {
        source_id: 'source-a',
        source_name: 'Replanned source',
        selected: true,
        supported: true,
        language: 'en',
        terms: ['Alternative'],
        purpose: 'disambiguation',
        candidate_id: 'missing-hypothesis',
        provenance: 'model_replanned_variant',
        temporal_scope: 'Current',
      },
      {
        source_id: 'source-b',
        source_name: 'Operator source',
        selected: true,
        supported: true,
        language: 'en',
        terms: ['Exact phrase'],
        purpose: 'challenge',
        provenance: 'operator_supplied_variant',
        temporal_scope: 'Current',
      },
    ],
  });
  const { candidate_hypotheses: _candidates, ...legacy } = parsed;
  render(<SavedCollectionPlan plan={legacy} />);
  expect(screen.getByText(/Hypothesis: missing-hypothesis/)).toBeInTheDocument();
  expect(screen.getByText(/Model-replanned search terms/)).toBeInTheDocument();
  expect(screen.getByText(/Operator-supplied language terms/)).toBeInTheDocument();
});
