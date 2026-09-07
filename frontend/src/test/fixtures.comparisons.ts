import type { AnnotationComparison, ComparisonSide } from '@/lib/api/annotationComparisons';
import {
  comparisonEvidenceSchema,
  comparisonJudgementSchema,
} from '@/lib/api/annotationComparisons';
import type { ClaimRevision } from '@/lib/api/claims';
import { report } from './fixtures';
import { reportAssessment } from './fixtures.reportAssessment';
export const comparisonClaim: ClaimRevision = {
  id: 'claim-revision-1',
  claim_id: 'claim-1',
  report_id: report.report.id,
  report_version_id: 'version-1',
  number: 1,
  previous_id: null,
  statement: 'Original analytical claim',
  kind: 'analytical_inference',
  state: 'proposed',
  citations: [
    {
      label: 'E1',
      relation: 'supporting',
      event_id: 'event-1',
      source_content_hash: 'hash',
      excerpt: { field: 'title', start: 0, end: 4, text: 'Text', sha256: 'hash' },
    },
  ],
  unresolved_conflicts: ['Collection is incomplete.'],
  reason: 'Initial evidence',
  model_origin: null,
  authored_by: 'user-1',
  created_at: '2026-09-01T00:00:00Z',
};
export const comparisonClaimAfter: ClaimRevision = {
  ...comparisonClaim,
  id: 'claim-revision-2',
  number: 2,
  previous_id: comparisonClaim.id,
  statement: 'Revised analytical claim',
  state: 'withdrawn',
  reason: 'Withdrawn after checking a counter-source.',
  created_at: '2026-09-07T00:00:00Z',
};
export const comparisonSide: ComparisonSide = {
  report_id: report.report.id,
  version_id: 'version-1',
  version_number: 1,
  title: report.report.title,
  period_from: null,
  period_to: null,
  version_created_at: report.version.created_at,
  data_cutoff: null,
  evidence_sha256: 'a'.repeat(64),
  content_sha256: 'b'.repeat(64),
  revisions: [comparisonClaim],
  identity_revisions: [],
  relationship_revisions: [],
  evidence: report.version.evidence.map((item) =>
    comparisonEvidenceSchema.parse({
      ...item,
      independence_key: item.independence_key ?? 'fixture',
      captured_at: item.captured_at ?? report.version.created_at,
      content_hash: item.content_hash ?? 'hash',
      reliability: item.reliability ?? 'B',
      credibility: item.credibility ?? 2,
      instrument: item.instrument ?? false,
      attributes: item.attributes ?? [],
      lon: item.lon ?? null,
      lat: item.lat ?? null,
    }),
  ),
  judgements: report.version.body.key_judgements.map((item) =>
    comparisonJudgementSchema.parse(item),
  ),
  assessment: reportAssessment,
};
export const annotationComparison: AnnotationComparison = {
  compared_by: 'user-1',
  method_version: 'ase-annotation-comparison-v1',
  generated_at: '2026-09-07T12:00:00Z',
  comparison_sha256: 'c'.repeat(64),
  before: comparisonSide,
  after: {
    ...comparisonSide,
    version_id: 'version-2',
    version_number: 2,
    revisions: [comparisonClaimAfter],
    assessment: { ...reportAssessment, method_version: 'another-frozen-method' },
  },
  correspondences: [],
  judgement_correspondences: [],
  annotation_changes: [
    {
      kind: 'claim',
      before_revision_id: comparisonClaim.id,
      after_revision_id: comparisonClaimAfter.id,
      correspondence: 'same_root',
      status: 'changed',
      changed_fields: ['statement', 'state', 'reason'],
    },
  ],
  evidence_changes: [
    {
      source_id: 'source-one',
      event_id: 'collision',
      before_label: 'E1',
      after_label: 'E2',
      status: 'changed',
      changed_fields: ['grade'],
    },
  ],
  confidence_changes: [
    {
      before_judgement_id: 'KJ1',
      after_judgement_id: 'KJ1',
      correspondence: 'exact_statement',
      status: 'changed',
      changed_fields: ['method_version', 'supporting_evidence', 'final_confidence'],
      explanations: [
        'Both support inputs and recorded confidence differ. Methods also differ; no unique cause is inferred.',
      ],
    },
  ],
  limitations: ['Selections are explicit, not a complete annotation inventory.'],
};
