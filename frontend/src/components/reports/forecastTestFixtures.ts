import { forecastSchema } from '@/lib/api/forecastSchemas';
import type { ClaimRevision } from '@/lib/api/claims';

export const forecastFixture = forecastSchema.parse({
  anchor: {
    id: 'ledger-1',
    kind: 'forecast',
    report_id: 'report-1',
    report_version_id: 'edition-1',
    claim_id: 'claim-1',
    claim_revision_id: 'reviewed-1',
    owner_id: 'owner-1',
    team_id: null,
    created_at: '2026-01-01T00:00:00Z',
    latest_ordinal: 1,
  },
  history: {
    versions: [
      {
        forecast_id: 'ledger-1',
        version_id: 'forecast-v1',
        version: 1,
        claim_id: 'claim-1',
        claim_version_id: 'reviewed-1',
        report_version_id: 'edition-1',
        issued_at: '2026-01-01T00:00:00Z',
        review_at: '2026-01-02T00:00:00Z',
        horizon_end: '2026-01-03T00:00:00Z',
        criterion: { description: 'Whether the road stays open' },
        likelihood: 'realistic_possibility',
        confidence: {
          source_quality: 'moderate',
          corroboration: 'low',
          coverage: 'low',
          limitation: 'A single source',
        },
        supporting: [
          { report_version_id: 'edition-1', evidence_id: 'E1', passage_id: 'a'.repeat(64) },
        ],
        contrary: [],
        policy_version: 'ase-forecast-ledger-v1',
      },
    ],
    decisions: [],
  },
});
export const reviewedClaim: ClaimRevision = {
  id: 'reviewed-1',
  claim_id: 'claim-1',
  report_id: 'report-1',
  report_version_id: 'edition-1',
  number: 2,
  previous_id: 'proposal-1',
  statement: 'The road is open',
  kind: 'reported_fact',
  state: 'reviewed',
  citations: [
    {
      label: 'E1',
      relation: 'supporting',
      event_id: 'event-1',
      source_content_hash: 'hash',
      excerpt: {
        field: 'title',
        start: 0,
        end: 16,
        text: 'The road is open',
        sha256: 'a'.repeat(64),
      },
    },
  ],
  unresolved_conflicts: [],
  reason: 'Checked source',
  model_origin: null,
  authored_by: 'owner-1',
  created_at: '2026-01-01T00:00:00Z',
};
