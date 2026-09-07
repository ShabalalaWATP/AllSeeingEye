import type { components } from '@/lib/api/types.gen';

export const sourceContext: components['schemas']['SourceSummaryOut'] = {
  id: 'bbc_world',
  name: 'BBC World',
  organisation: 'BBC',
  parent_organisation: null,
  category: 'news',
  language: 'en',
  reliability: 'B',
  rating: {
    policy_version: 'qa-editorial-v1',
    status: 'editorial',
    assessed_grade: 'B',
    basis: 'Fixture editorial assignment, not a measured accuracy score.',
    scope: 'Published reporting within the stated editorial remit.',
    limitations: ['Individual claims require separate assessment.'],
    provenance_role: 'publisher',
    publisher_reliability_assessed: true,
    reviewed_at: null,
  },
};

export const researchReceipt: components['schemas']['ResearchReceiptOut'] = {
  time_basis: 'publication',
  question: '[QA] What has changed in Ukraine?',
  mode: 'detailed',
  focus: 'general',
  languages: ['en', 'fr'],
  terms: ['Ukraine', 'shelling'],
  since: '2026-09-01T00:00:00Z',
  until: '2026-09-04T00:00:00Z',
  collected_items: 1,
  policy_version: 'qa-collection-v1',
  attempts: [
    {
      source_id: 'bbc_world',
      source_name: 'BBC World',
      purpose: 'baseline',
      status: 'completed',
      result_count: 1,
      explanation: 'One matching item collected.',
      language: 'en',
    },
    {
      source_id: 'qa_empty',
      source_name: 'QA empty feed',
      purpose: 'baseline',
      status: 'empty',
      result_count: 0,
      explanation: 'No matching items in the publication period.',
      language: 'fr',
    },
    {
      source_id: 'qa_unavailable',
      source_name: 'QA unavailable feed',
      purpose: 'baseline',
      status: 'unavailable',
      result_count: 0,
      explanation: 'Feed unavailable for this run.',
      language: null,
    },
    {
      source_id: 'qa_failed',
      source_name: 'QA failed feed',
      purpose: 'baseline',
      status: 'failed',
      result_count: 0,
      explanation: 'Collection request failed.',
      language: 'en',
    },
  ],
};

export const citationChecks: components['schemas']['ReportCitationChecksOut'] = {
  method_version: 'qa-literal-v1',
  limitations: [
    'Literal excerpt checks do not establish semantic entailment or truth.',
    'These checks do not change grades, likelihood or confidence.',
  ],
  judgements: [
    {
      judgement_id: 'KJ1',
      status: 'review_required',
      reasons: ['A numeric cue needs contextual review.'],
      citations: [
        {
          label: 'E1',
          relation: 'supporting',
          status: 'review_required',
          evidence_id: 'e1',
          source_content_hash: 'qa-source-hash',
          excerpt: {
            field: 'summary',
            start: 0,
            end: 19,
            text: 'Overnight shelling.',
            sha256: 'qa-excerpt-hash',
          },
          indicators: [
            {
              kind: 'number_mismatch',
              claim_values: ['12'],
              excerpt_values: [],
              explanation: 'The claim number is absent from the frozen snippet.',
            },
          ],
          reasons: ['Exact text is present in the saved source snippet.'],
        },
      ],
    },
  ],
};
