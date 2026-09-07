import type { IdentityRevision, IdentityRoot } from '@/lib/api/identities';

export const identityRevision: IdentityRevision = {
  id: 'identity-revision-1',
  decision_id: 'identity-1',
  report_id: 'report-1',
  report_version_id: 'version-1',
  number: 1,
  previous_id: null,
  subject: '中国公司 000123',
  candidate: {
    candidate: {
      evidence_label: 'E1',
      identifiers: [{ namespace: 'lei', value: '00123456789012345678' }],
      aliases: [{ namespace: 'name', value: '中国公司' }],
      declared_match_status: null,
      status: 'unverified_candidate',
    },
    event_id: 'event-1',
    source_id: 'gleif',
    source_content_hash: 'hash',
    attributes: [{ key: 'reported_jurisdiction', value: 'CN' }],
  },
  disposition: 'unresolved',
  rationale: 'Registry identity is ambiguous.',
  unresolved_conflicts: ['First line\nSecond line'],
  citations: [],
  authored_by: 'user-1',
  created_at: '2026-09-07T00:00:00Z',
};
export const identityRoot: IdentityRoot = {
  id: 'identity-1',
  report_id: 'report-1',
  report_version_id: 'version-1',
  report_version_number: 1,
  created_by: 'user-1',
  team_id: null,
  subject: identityRevision.subject,
  candidate_label: 'E1',
  evidence_sha256: 'hash',
  latest_revision_id: identityRevision.id,
  created_at: identityRevision.created_at,
};
