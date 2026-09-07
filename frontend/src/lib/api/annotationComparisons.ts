import { z } from 'zod';
import { apiCall, apiBlob } from './client';
import { claimRevisionSchema } from './claims';
import { identityRevisionSchema } from './identities';
import { relationshipRevisionSchema } from './relationships';
import { evidenceItemSchema, keyJudgementSchema, reportSummarySchema } from './reports';
import { evidenceGeometrySchema } from './observations';
import { reportAssessmentSchema } from './reportAssessment';
import type { components } from './types.gen';
export type AnnotationComparisonInput = components['schemas']['AnnotationComparisonIn'];
export type AnnotationComparisonExportInput = components['schemas']['AnnotationComparisonExportIn'];
export type AnnotationComparison = components['schemas']['AnnotationComparisonOut'];
export type ComparisonSide = components['schemas']['ComparisonSide'];
const kind = z.enum(['claim', 'identity', 'relationship']);
const status = z.enum(['unchanged', 'changed', 'added', 'removed']);
const ids = z.string().nullable();
const fields = z.array(z.string());
export const comparisonEvidenceSchema = evidenceItemSchema.extend({
  independence_key: evidenceItemSchema.shape.independence_key.unwrap(),
  captured_at: evidenceItemSchema.shape.captured_at.unwrap(),
  content_hash: evidenceItemSchema.shape.content_hash.unwrap(),
  reliability: evidenceItemSchema.shape.reliability.unwrap(),
  credibility: evidenceItemSchema.shape.credibility.unwrap(),
  instrument: evidenceItemSchema.shape.instrument.unwrap(),
  attributes: evidenceItemSchema.shape.attributes.unwrap(),
  lon: evidenceItemSchema.shape.lon.unwrap(),
  lat: evidenceItemSchema.shape.lat.unwrap(),
  title_en: evidenceItemSchema.shape.title_en.default(null),
  language: evidenceItemSchema.shape.language.default(null),
  observed_at: evidenceItemSchema.shape.observed_at.default(null),
  story_id: evidenceItemSchema.shape.story_id.default(null),
  geo_confidence: evidenceItemSchema.shape.geo_confidence.default(null),
  source_rating: evidenceItemSchema.shape.source_rating.default(null),
  geometry: evidenceGeometrySchema
    .omit({ geometry: true, sha256: true })
    .extend({ source_geometry: z.string() })
    .nullable()
    .default(null),
  observation: evidenceItemSchema.shape.observation.default(null),
  project: evidenceItemSchema.shape.project.default(null),
}) satisfies z.ZodType<components['schemas']['EvidenceItem']>;
export const comparisonJudgementSchema = keyJudgementSchema.extend({
  probability: z.enum([
    'remote_chance',
    'highly_unlikely',
    'unlikely',
    'realistic_possibility',
    'likely',
    'highly_likely',
    'almost_certain',
  ]),
  confidence: z.enum(['low', 'moderate', 'high']),
  change_from_previous: z
    .enum(['new', 'unchanged', 'strengthened', 'weakened', 'reversed'])
    .nullable(),
}) satisfies z.ZodType<components['schemas']['KeyJudgement']>;
const sideSchema = z.object({
  report_id: z.string(),
  version_id: z.string(),
  version_number: z.number().int().positive(),
  title: z.string(),
  period_from: ids,
  period_to: ids,
  version_created_at: z.string(),
  data_cutoff: ids,
  evidence_sha256: z.string(),
  content_sha256: z.string(),
  revisions: z.array(claimRevisionSchema).max(20),
  identity_revisions: z.array(identityRevisionSchema).max(20),
  relationship_revisions: z.array(relationshipRevisionSchema).max(20),
  evidence: z.array(comparisonEvidenceSchema),
  judgements: z.array(comparisonJudgementSchema),
  assessment: reportAssessmentSchema.nullable(),
});
export const annotationComparisonSchema = z.object({
  compared_by: z.string(),
  method_version: z.string(),
  generated_at: z.string(),
  comparison_sha256: z.string().regex(/^[a-f0-9]{64}$/),
  before: sideSchema,
  after: sideSchema,
  correspondences: z
    .array(
      z.object({
        kind,
        before_revision_id: z.string(),
        after_revision_id: z.string(),
        rationale: z.string().max(500),
      }),
    )
    .max(20),
  judgement_correspondences: z
    .array(
      z.object({
        before_judgement_id: z.string(),
        after_judgement_id: z.string(),
        rationale: z.string().max(500),
      }),
    )
    .max(20),
  annotation_changes: z.array(
    z.object({
      kind,
      before_revision_id: ids,
      after_revision_id: ids,
      correspondence: z.enum(['same_root', 'operator_declared', 'unmatched']),
      status,
      changed_fields: fields,
    }),
  ),
  evidence_changes: z.array(
    z.object({
      source_id: z.string(),
      event_id: z.string(),
      before_label: ids,
      after_label: ids,
      status,
      changed_fields: fields,
    }),
  ),
  confidence_changes: z.array(
    z.object({
      before_judgement_id: ids,
      after_judgement_id: ids,
      correspondence: z.enum(['exact_statement', 'operator_declared', 'unmatched']),
      status,
      changed_fields: fields,
      explanations: fields,
    }),
  ),
  limitations: fields,
}) satisfies z.ZodType<AnnotationComparison>;
export function compareAnnotations(body: AnnotationComparisonInput, signal: AbortSignal) {
  return apiCall('/api/annotation-comparisons', {
    method: 'POST',
    body,
    signal,
    schema: annotationComparisonSchema,
  });
}
export function exportAnnotationComparison(
  body: AnnotationComparisonExportInput,
  signal: AbortSignal,
) {
  return apiBlob('/api/annotation-comparisons/export', {
    method: 'POST',
    body,
    signal,
    headers: { Accept: 'application/json' },
  });
}

export function listComparisonReports(query: string, offset: number, signal: AbortSignal) {
  const params = new URLSearchParams({ q: query, offset: String(offset), limit: '20' });
  return apiCall(`/api/annotation-comparisons/reports?${params}`, {
    signal,
    schema: z.object({
      items: z.array(reportSummarySchema).max(50),
      total: z.number().int().nonnegative(),
      offset: z.number().int().nonnegative(),
      limit: z.number().int().positive(),
    }) satisfies z.ZodType<components['schemas']['ComparisonReportsOut']>,
  });
}
