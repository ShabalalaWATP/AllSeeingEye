import { z } from 'zod';
import { scopedMutation } from '@/lib/workspaceAccess';
import { apiCall } from './client';
import type { components } from './types.gen';

export type ClaimRevision = components['schemas']['ClaimRevision'];
export type ClaimCreate = components['schemas']['ClaimCreateIn'];
export type ClaimUpdate = components['schemas']['ClaimUpdateIn'];
export type ClaimGenerationResult = components['schemas']['ClaimGenerationResult'];
export const claimRevisionSchema = z.object({
  id: z.string(),
  claim_id: z.string(),
  report_id: z.string(),
  report_version_id: z.string(),
  number: z.number().int().positive(),
  previous_id: z.string().nullable(),
  statement: z.string(),
  kind: z.enum(['reported_fact', 'analytical_inference']),
  state: z.enum(['proposed', 'reviewed', 'withdrawn']),
  citations: z
    .array(
      z.object({
        label: z.string(),
        relation: z.enum(['supporting', 'opposing', 'context']),
        event_id: z.string(),
        source_content_hash: z.string(),
        excerpt: z.object({
          field: z.enum(['title', 'summary']),
          start: z.number().int().nonnegative(),
          end: z.number().int().positive(),
          text: z.string(),
          sha256: z.string(),
        }),
      }),
    )
    .min(1)
    .max(20),
  unresolved_conflicts: z.array(z.string()).max(20),
  reason: z.string(),
  model_origin: z
    .object({
      batch_id: z.string(),
      profile_id: z.string(),
      profile_revision: z.number().int().positive(),
      provider: z.string(),
      requested_model: z.string(),
      returned_model: z.string(),
      input_sha256: z.string(),
      method_version: z.string(),
      generated_at: z.string(),
    })
    .nullable()
    .default(null),
  authored_by: z.string(),
  created_at: z.string(),
}) satisfies z.ZodType<ClaimRevision>;
const detailSchema = z.object({
  root: z.object({
    id: z.string(),
    report_id: z.string(),
    report_version_id: z.string(),
    report_version_number: z.number().int().positive(),
    created_by: z.string(),
    team_id: z.string().nullable(),
    evidence_sha256: z.string(),
    latest_revision_id: z.string(),
    created_at: z.string(),
  }),
  revision: claimRevisionSchema,
}) satisfies z.ZodType<components['schemas']['ClaimDetailOut']>;
const pageSchema = z.object({
  items: z.array(claimRevisionSchema).max(20),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
}) satisfies z.ZodType<components['schemas']['ClaimPageOut']>;
export function listClaims(reportId: string, version: number, offset: number, signal: AbortSignal) {
  const query = new URLSearchParams({
    report_id: reportId,
    version_number: String(version),
    limit: '20',
    offset: String(offset),
  });
  return apiCall(`/api/claims?${query}`, { schema: pageSchema, signal });
}
export function fetchClaim(id: string, revisionId: string | null, signal: AbortSignal) {
  const suffix = revisionId ? `/revisions/${encodeURIComponent(revisionId)}` : '';
  return apiCall(`/api/claims/${encodeURIComponent(id)}${suffix}`, {
    schema: detailSchema,
    signal,
  });
}
export function createClaim(body: ClaimCreate, signal: AbortSignal): Promise<ClaimRevision> {
  return scopedMutation(() =>
    apiCall('/api/claims', { method: 'POST', body, schema: claimRevisionSchema, signal }),
  );
}
export function generateClaims(reportId: string, version: number, signal: AbortSignal) {
  return scopedMutation(() =>
    apiCall('/api/claims/generate', {
      method: 'POST',
      body: { report_id: reportId, version_number: version },
      signal,
      schema: z.object({
        status: z.enum(['completed', 'empty', 'invalid', 'unavailable', 'unsupported']),
        items: z.array(claimRevisionSchema).max(20),
      }) satisfies z.ZodType<ClaimGenerationResult>,
    }),
  );
}

export function updateClaim(
  id: string,
  body: ClaimUpdate,
  signal: AbortSignal,
): Promise<ClaimRevision> {
  return scopedMutation(() =>
    apiCall(`/api/claims/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body,
      schema: claimRevisionSchema,
      signal,
    }),
  );
}
