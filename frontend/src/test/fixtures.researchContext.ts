import type { components } from '@/lib/api/types.gen';

export const researchContext: components['schemas']['ResearchContextOut'] = {
  method_version: 'qa-context-v1',
  limitations: ['Captured names and relationships are unverified.'],
  timeline: [
    {
      evidence_label: 'E1',
      title: 'Saved source title',
      published_at: '2026-09-01T00:00:00Z',
      captured_at: '2026-09-04T00:00:00Z',
      observed_at: null,
      timestamp_basis: 'registry_snapshot',
      date_precision: 'day',
      current_snapshot: true,
      record_kind: 'registration',
      temporal_attributes: [{ key: 'registered_date_raw', value: '2020' }],
      limitations: ['Publication order does not establish event order.'],
    },
  ],
  identity_candidates: [
    {
      evidence_label: 'E1',
      identifiers: [{ namespace: 'company_number', value: 'QA-123' }],
      aliases: [{ namespace: 'name', value: '<script>Declared alias</script>' }],
      declared_match_status: 'name_candidate',
      status: 'unverified_candidate',
    },
  ],
  source_chains: [
    {
      evidence_label: 'E1',
      collector_source_id: 'qa_collector',
      relation: 'declared_publisher',
      declared_name: 'Example publisher',
      declared_id: 'QA-123',
      declared_url: 'https://example.test/source',
      status: 'unverified_attribution',
    },
    {
      evidence_label: 'E1',
      collector_source_id: 'qa_collector',
      relation: 'declared_account',
      declared_name: 'Unsafe URL fixture',
      declared_id: null,
      declared_url: 'javascript:alert(1)',
      status: 'unverified_attribution',
    },
  ],
  source_relationships: [
    {
      evidence_labels: ['E1', 'E2'],
      reasons: ['Possible copy based on recorded provenance.'],
      shared_parent: 'Declared parent',
      status: 'unverified_relationship',
    },
  ],
};

export const reportChallenge: components['schemas']['ReportChallengeOut'] = {
  method_version: 'qa-challenge-v1',
  redrafted: true,
  request_limit: 6,
  seconds_limit: 45,
  limitations: ['Review is automated and does not establish semantic proof.'],
  searches: [
    {
      judgement_id: 'KJ1',
      statement: 'Initial judgement wording.',
      terms: ['counterevidence'],
      status: 'attempted',
      attempts: [
        {
          source_id: 'qa_feed',
          source_name: 'QA feed',
          status: 'budget_exhausted',
          result_count: 0,
          explanation: 'No request admitted within the shared limit.',
          language: 'en',
        },
      ],
      collected_items: 0,
      selected_event_ids: [],
      explanation: 'Collection pass ran; see individual provider outcomes.',
    },
  ],
  reviews: [
    {
      judgement_id: 'KJ1',
      statement: 'Final judgement wording.',
      status: 'completed',
      explanation: 'Review of the final draft.',
      advocacy: {
        target: 'KJ1',
        argument: 'A different explanation remains possible.',
        evidence: ['E1'],
        lower_confidence: true,
        rationale: 'Saved evidence is incomplete.',
        confidence_before: 'moderate',
        confidence_after: 'low',
      },
    },
    {
      judgement_id: 'KJ2',
      statement: 'A second final judgement.',
      status: 'unavailable',
      explanation: 'Review service was unavailable.',
      advocacy: null,
    },
  ],
};
