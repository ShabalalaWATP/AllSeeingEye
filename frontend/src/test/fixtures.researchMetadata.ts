import type { components } from '@/lib/api/types.gen';

export const sourceContext: components['schemas']['SourceSummaryOut'] = {
  id: 'bbc_world',
  name: 'BBC World',
  organisation: 'BBC',
  parent_organisation: null,
  category: 'news',
  language: 'en',
  reliability: 'B',
  coverage_scope: 'global',
  coverage_countries: [],
  coverage_regions: [],
  coverage_note: 'International reporting focus.',
  kind: 'rss',
  requires_key: false,
  collection_mode: 'scheduled',
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
  connection: {
    state: 'connected',
    enabled: true,
    environment_disabled: false,
    active: true,
    requirement: null,
    health: {
      status: 'healthy',
      last_success: '2026-09-12T12:00:00Z',
      last_error_at: null,
      consecutive_failures: 0,
      items_last_poll: 12,
      next_poll_at: null,
      polls: 3,
      blocked_reason: null,
    },
    detail: 'Collecting on schedule.',
  },
};

export const platformConnections: components['schemas']['PlatformConnectionOut'][] = [
  {
    id: 'assessment_model',
    name: 'AI assessment model',
    purpose: 'Writes briefings, reports and the Eye assistant’s answers.',
    state: 'key_missing',
    requirement: {
      kind: 'model',
      satisfied: false,
      origin: 'none',
      setting: null,
      note: 'No enabled model profile can play this role. Add one under Admin, Models.',
      optional: false,
    },
    detail: 'No model is available for your personal workspace.',
  },
  {
    id: 'os_maps',
    name: 'Ordnance Survey maps',
    purpose: 'OS Road, Outdoor and Light base layers on the map.',
    state: 'connected',
    requirement: {
      kind: 'api_key',
      satisfied: true,
      origin: 'environment',
      setting: 'ASE_OS_MAPS_KEY',
      note: 'ASE_OS_MAPS_KEY is set.',
      optional: false,
    },
    detail: 'Configured.',
  },
  {
    id: 'alert_webhook',
    name: 'Alert webhook',
    purpose: 'Posts fired indicators to an external https endpoint.',
    state: 'not_configured',
    requirement: {
      kind: 'endpoint',
      satisfied: false,
      origin: 'none',
      setting: 'ASE_ALERT_WEBHOOK_URL',
      note: 'Set ASE_ALERT_WEBHOOK_URL on the server.',
      optional: true,
    },
    detail: 'Optional.',
  },
];

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

/** Default server capabilities: AI research is ready, so no set-up notice appears. */
export const serverCapabilities: components['schemas']['CapabilitiesOut'] = {
  os_maps: false,
  os_layers: [],
  ai_research: true,
};
