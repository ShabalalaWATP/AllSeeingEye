import { z } from 'zod';

import { apiCall } from './client';
import { ApiError } from './errors';
import type { ResearchBrief } from './researchBriefSchema';

const preflightSchema = z.object({
  brief_id: z.uuid(),
  revision: z.number().int().positive(),
  title: z.string(),
  as_of: z.iso.datetime({ offset: true }),
  scope: z.object({
    country_isos: z.array(z.string()),
    focus: z.string(),
    subject: z.string().nullable(),
    area_sha256: z.string().nullable(),
    saved_map_resolution_required: z.boolean(),
    linked_context_checks_required: z.boolean(),
  }),
  since: z.iso.datetime({ offset: true }),
  until: z.iso.datetime({ offset: true }),
  observation_policy: z.string(),
  time_basis: z.enum(['publication', 'acquisition_or_publication', 'recorded_time']),
  forecast_horizon_days: z.number().int().positive().nullable(),
  question: z.string(),
  requirements: z.array(
    z.object({
      id: z.string(),
      question: z.string(),
      required: z.boolean(),
      priority: z.number().int(),
    }),
  ),
  budget: z.object({
    tier: z.enum(['quick', 'detailed', 'advanced']),
    required_question_ceiling: z.number().int().positive(),
    tier_source_operations: z.number().int().nonnegative(),
    tier_collection_seconds: z.number().int().nonnegative(),
    source_operation_ceiling: z.number().int().nonnegative(),
    collection_second_ceiling: z.number().int().nonnegative(),
    model_call_ceiling: z.number().int().nonnegative(),
    output_token_ceiling: z.number().int().nonnegative(),
    reservations_made: z.literal(false),
  }),
  source_policy: z.string(),
  sources: z.array(
    z.object({
      capability: z.object({
        id: z.string(),
        name: z.string(),
        route: z.string(),
        support: z.object({ constraints: z.string() }),
      }),
      readiness: z.string(),
      candidate_unverified: z.boolean(),
      exclusion_reasons: z.array(z.string()),
      date_note: z.string(),
    }),
  ),
  unknown_source_ids: z.array(z.string()),
  gaps: z.array(z.object({ id: z.string(), name: z.string(), reason: z.string() })),
  candidate_provider_ids: z.array(z.string()),
  known_origin_group_count: z.number().int().nonnegative(),
  unknown_origin_capability_count: z.number().int().nonnegative(),
  review_reasons: z.array(z.string()),
  preview_only: z.literal(true),
  admission_checked: z.literal(false),
  source_relevance_ranked: z.literal(false),
  provider_calls: z.literal(0),
  model_calls: z.literal(0),
  model_compatibility: z.literal('not_checked'),
  policy_version: z.string(),
  duration_note: z.string(),
  coverage_note: z.string(),
});

export type ResearchPreflight = z.infer<typeof preflightSchema>;

export async function fetchBriefPreflight(brief: ResearchBrief, signal: AbortSignal) {
  const result = await apiCall(
    `/api/research/briefs/${encodeURIComponent(brief.identity.id)}/revisions/${brief.identity.revision}/preflight`,
    { schema: z.object({ preflight: preflightSchema }), signal },
  );
  if (
    result.preflight.brief_id !== brief.identity.id ||
    result.preflight.revision !== brief.identity.revision
  )
    throw new ApiError(502, 'invalid_response', 'The preview returned a different brief revision.');
  return result.preflight;
}
