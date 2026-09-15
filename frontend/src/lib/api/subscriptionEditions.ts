import { z } from 'zod';

import { apiCall } from './client';

const intervalSchema = z.object({ start: z.string(), end: z.string() });

const comparisonSchema = z.object({
  previous_version_id: z.uuid().nullable(),
  current_version_id: z.uuid(),
  state: z.enum([
    'failure',
    'insufficient_coverage',
    'significant_contradiction_or_correction',
    'assessment_changed',
    'new_evidence_broadly_unchanged_assessment',
    'no_new_relevant_captured_evidence',
  ]),
  reasons: z.array(
    z.enum([
      'current_run_failed',
      'baseline_unavailable',
      'baseline_incompatible',
      'provider_outage',
      'coverage_inadequate',
      'significant_contradiction',
      'source_correction',
      'claim_inventory_changed',
      'claim_mapping_unresolved',
      'claim_meaning_changed',
      'likelihood_changed',
      'horizon_changed',
      'support_changed',
      'opposition_changed',
      'assumptions_changed',
      'indicators_changed',
      'new_relevant_evidence',
      'syndicated_duplicates_only',
      'adequate_coverage_no_new_evidence',
    ]),
  ),
  changed_claims: z.number().int().nonnegative(),
  corrected_evidence: z.number().int().nonnegative(),
  novel_evidence: z.number().int().nonnegative(),
  syndicated_duplicates: z.number().int().nonnegative(),
  summary: z.string().max(300),
});

export const subscriptionEditionSchema = z.object({
  id: z.uuid(),
  subscription_id: z.uuid(),
  trigger: z.enum(['scheduled', 'catch_up', 'run_now', 'baseline']),
  due_at_utc: z.string().nullable(),
  frozen_revision: z.number().int().positive(),
  requested: intervalSchema,
  effective_intervals: z.array(intervalSchema),
  gaps: z.array(intervalSchema),
  workflow: z.enum([
    'pending',
    'queued',
    'running',
    'retry_wait',
    'paused',
    'blocked',
    'completed',
    'failed',
    'cancelled',
    'skipped',
  ]),
  report_quality: z.enum(['absent', 'ready', 'needs_review', 'failed']),
  coverage: z.enum(['complete_for_plan', 'partial', 'insufficient', 'unknown']),
  job_id: z.uuid().nullable(),
  report_id: z.uuid().nullable(),
  version_id: z.uuid().nullable(),
  accepted_as_baseline: z.boolean().default(false),
  comparison: comparisonSchema.nullable().default(null),
  safe_reason: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type SubscriptionEdition = z.infer<typeof subscriptionEditionSchema>;

const editionPageSchema = z.object({
  items: z.array(subscriptionEditionSchema),
  limit: z.number().int(),
  offset: z.number().int(),
});

export function fetchSubscriptionEditions(
  subscriptionId: string,
  offset = 0,
  signal?: AbortSignal,
) {
  return apiCall(
    `/api/schedules/${encodeURIComponent(subscriptionId)}/editions?limit=10&offset=${offset}`,
    {
      schema: editionPageSchema,
      ...(signal ? { signal } : {}),
    },
  );
}
