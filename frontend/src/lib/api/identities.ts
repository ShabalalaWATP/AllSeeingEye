import { z } from 'zod';
import { scopedMutation } from '@/lib/workspaceAccess';
import { apiCall } from './client';
import { claimRevisionSchema } from './claims';
import { researchContextSchema } from './researchContext';
import { evidenceAttributeSchema } from './reportResearch';
import type { components } from './types.gen';

export type IdentityRevision = components['schemas']['IdentityDecisionRevision'];
export type IdentityCreate = components['schemas']['IdentityCreateIn'];
export type IdentityUpdate = components['schemas']['IdentityUpdateIn'];
export type IdentityRoot = components['schemas']['IdentityDecisionRoot'];
export type IdentityCandidate = components['schemas']['ResearchIdentityCandidate'];

export const identityRevisionSchema = z.object({
  id: z.string(),
  decision_id: z.string(),
  report_id: z.string(),
  report_version_id: z.string(),
  number: z.number().int().min(1).max(100),
  previous_id: z.string().nullable(),
  subject: z.string(),
  candidate: z.object({
    candidate: researchContextSchema.shape.identity_candidates.element,
    event_id: z.string(),
    source_id: z.string(),
    source_content_hash: z.string(),
    attributes: z.array(evidenceAttributeSchema),
  }),
  disposition: z.enum(['matched', 'rejected', 'unresolved', 'withdrawn']),
  rationale: z.string(),
  unresolved_conflicts: z.array(z.string()).max(20),
  citations: z.array(claimRevisionSchema.shape.citations.element).max(20),
  authored_by: z.string(),
  created_at: z.string(),
}) satisfies z.ZodType<IdentityRevision>;

const detailSchema = z.object({
  root: z.object({
    id: z.string(),
    report_id: z.string(),
    report_version_id: z.string(),
    report_version_number: z.number().int().positive(),
    created_by: z.string(),
    team_id: z.string().nullable(),
    subject: z.string(),
    candidate_label: z.string(),
    evidence_sha256: z.string(),
    latest_revision_id: z.string(),
    created_at: z.string(),
  }),
  revision: identityRevisionSchema,
}) satisfies z.ZodType<components['schemas']['IdentityDetailOut']>;
const pageSchema = z.object({
  items: z.array(identityRevisionSchema).max(20),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
}) satisfies z.ZodType<components['schemas']['IdentityPageOut']>;

export function listIdentities(
  reportId: string,
  version: number,
  offset: number,
  signal: AbortSignal,
) {
  const query = new URLSearchParams({
    report_id: reportId,
    version_number: String(version),
    limit: '20',
    offset: String(offset),
  });
  return apiCall(`/api/identity-reviews?${query}`, { schema: pageSchema, signal });
}
export function fetchIdentity(id: string, revisionId: string | null, signal: AbortSignal) {
  const suffix = revisionId ? `/revisions/${encodeURIComponent(revisionId)}` : '';
  return apiCall(`/api/identity-reviews/${encodeURIComponent(id)}${suffix}`, {
    schema: detailSchema,
    signal,
  });
}
export function createIdentity(body: IdentityCreate, signal: AbortSignal) {
  return scopedMutation(() =>
    apiCall('/api/identity-reviews', {
      method: 'POST',
      body,
      schema: identityRevisionSchema,
      signal,
    }),
  );
}
export function updateIdentity(id: string, body: IdentityUpdate, signal: AbortSignal) {
  return scopedMutation(() =>
    apiCall(`/api/identity-reviews/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body,
      schema: identityRevisionSchema,
      signal,
    }),
  );
}
