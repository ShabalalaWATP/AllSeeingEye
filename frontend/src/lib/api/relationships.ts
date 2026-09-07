import { z } from 'zod';
import { apiCall } from './client';
import { scopedMutation } from '@/lib/workspaceAccess';
import { claimRevisionSchema } from './claims';
import { evidenceAttributeSchema } from './reportResearch';
import type { components } from './types.gen';
export const relationshipAssertionSchema = z.object({
  evidence_label: z.string(),
  event_id: z.string(),
  source_id: z.string(),
  source_content_hash: z.string(),
  child_lei: z.string(),
  parent_lei: z.string(),
  kind: z.enum(['direct', 'ultimate']),
  relationship_type: z.string(),
  captured_at: z.string(),
  published_at: z.string().nullable(),
  attributes: z.array(evidenceAttributeSchema),
  periods: z
    .array(
      z.object({
        type: z.string().max(50),
        startDate: z.string().max(50),
        endDate: z.string().max(50),
      }),
    )
    .max(20)
    .nullable(),
  periods_state: z.enum(['parsed', 'missing', 'unavailable']),
}) satisfies z.ZodType<RelationshipAssertion>;
export const relationshipRevisionSchema = z.object({
  id: z.string(),
  relationship_id: z.string(),
  report_id: z.string(),
  report_version_id: z.string(),
  number: z.number().int().min(1).max(100),
  previous_id: z.string().nullable(),
  assertion: relationshipAssertionSchema,
  disposition: z.enum(['supported', 'disputed', 'unresolved', 'withdrawn']),
  rationale: z.string().max(1200),
  unresolved_conflicts: z.array(z.string().max(1200)).max(20),
  citations: z.array(claimRevisionSchema.shape.citations.element).max(20),
  authored_by: z.string(),
  created_at: z.string(),
}) satisfies z.ZodType<RelationshipRevision>;
const rootSchema = z.object({
  id: z.string(),
  report_id: z.string(),
  report_version_id: z.string(),
  report_version_number: z.number().int().positive(),
  created_by: z.string(),
  team_id: z.string().nullable(),
  evidence_label: z.string(),
  evidence_sha256: z.string(),
  latest_revision_id: z.string(),
  created_at: z.string(),
}) satisfies z.ZodType<RelationshipRoot>;
const detailSchema = z.object({
  root: rootSchema,
  revision: relationshipRevisionSchema,
}) satisfies z.ZodType<components['schemas']['RelationshipDetailOut']>;
const pageSchema = z.object({
  items: z.array(relationshipRevisionSchema).max(20),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
}) satisfies z.ZodType<components['schemas']['RelationshipPageOut']>;
const assertionsSchema = z.object({
  items: z.array(relationshipAssertionSchema),
  unavailable_labels: z.array(z.string()),
  review_ids: z.record(z.string(), z.string()),
}) satisfies z.ZodType<components['schemas']['RelationshipAssertionsOut']>;
export type RelationshipAssertion = components['schemas']['RelationshipAssertionSnapshot'];
export type RelationshipRevision = components['schemas']['RelationshipReviewRevision'];
export type RelationshipRoot = components['schemas']['RelationshipReviewRoot'];
export type RelationshipCreate = components['schemas']['RelationshipCreateIn'];
export type RelationshipUpdate = components['schemas']['RelationshipUpdateIn'];
function query(reportId: string, version: number) {
  return new URLSearchParams({ report_id: reportId, version_number: String(version) });
}
export function listRelationshipAssertions(reportId: string, version: number, signal: AbortSignal) {
  return apiCall(`/api/relationship-reviews/assertions?${query(reportId, version)}`, {
    schema: assertionsSchema,
    signal,
  });
}
export function listRelationships(
  reportId: string,
  version: number,
  offset: number,
  signal: AbortSignal,
) {
  const params = query(reportId, version);
  params.set('limit', '20');
  params.set('offset', String(offset));
  return apiCall(`/api/relationship-reviews?${params}`, { schema: pageSchema, signal });
}
export function fetchRelationship(id: string, revisionId: string | null, signal: AbortSignal) {
  const suffix = revisionId ? `/revisions/${encodeURIComponent(revisionId)}` : '';
  return apiCall(`/api/relationship-reviews/${encodeURIComponent(id)}${suffix}`, {
    schema: detailSchema,
    signal,
  });
}
export function createRelationship(body: RelationshipCreate, signal: AbortSignal) {
  return scopedMutation(() =>
    apiCall('/api/relationship-reviews', {
      method: 'POST',
      body,
      schema: relationshipRevisionSchema,
      signal,
    }),
  );
}
export function updateRelationship(id: string, body: RelationshipUpdate, signal: AbortSignal) {
  return scopedMutation(() =>
    apiCall(`/api/relationship-reviews/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body,
      schema: relationshipRevisionSchema,
      signal,
    }),
  );
}
