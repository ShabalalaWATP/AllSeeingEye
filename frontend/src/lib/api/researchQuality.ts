import { z } from 'zod';

import { apiCall } from './client';
import type { components } from './types.gen';

type Schemas = components['schemas'];
const count = z.number().int().nonnegative();
const key = z.string().max(200);
const label = z.string().max(200);

const findingSchema = z.object({
  key,
  rule: z.string().max(60),
  severity: z.string().max(20),
  versions: count,
  occurrences: count,
}) satisfies z.ZodType<Schemas['QualityFindingOut']>;

const versionGroupSchema = z.object({
  key,
  label,
  versions: count,
  ready: count,
  needs_review: count,
  failed: count,
  findings: z.array(findingSchema),
  receipts: z.object({
    versions_with_receipts: count,
    versions_without_receipts: count,
    attempts: count,
    completed: count,
    empty: count,
    unavailable: count,
    other_unsuccessful: count,
    versions_with_empty_or_unavailable: count,
  }),
  usage: z.object({
    versions_with_usage: count,
    versions_without_usage: count,
    prompt_tokens: count,
    completion_tokens: count,
    prompt_tokens_per_version: count.nullable(),
    completion_tokens_per_version: count.nullable(),
  }),
}) satisfies z.ZodType<Schemas['QualityVersionGroupOut']>;

const jobGroupSchema = z.object({
  key,
  label,
  jobs: count,
  queued: count,
  running: count,
  paused: count,
  completed: count,
  needs_review: count,
  failed: count,
  failed_without_version: count,
  failed_with_version: count,
  failure_codes: z.array(z.object({ code: z.string().max(120), jobs: count })),
}) satisfies z.ZodType<Schemas['QualityJobGroupOut']>;

const bounds = { bound: count, in_window: count, counted: count, bound_reached: z.boolean() };

export const researchQualitySchema = z.object({
  generated_at: z.string(),
  window_days: z.number().int().positive(),
  since: z.string(),
  versions: z.object({
    ...bounds,
    overall: versionGroupSchema,
    by_template: z.array(versionGroupSchema),
    by_depth: z.array(versionGroupSchema),
    by_connection: z.array(versionGroupSchema),
  }),
  jobs: z.object({
    ...bounds,
    overall: jobGroupSchema,
    by_template: z.array(jobGroupSchema),
    by_depth: z.array(jobGroupSchema),
    by_model: z.array(jobGroupSchema),
  }),
  citation_checks: z.object({
    available: z.boolean(),
    note: z.string().max(500),
    bound: z.number().int().nonnegative(),
    in_window: z.number().int().nonnegative(),
    counted: z.number().int().nonnegative(),
    bound_reached: z.boolean(),
    current_verdicts: z.number().int().nonnegative(),
    superseded_verdicts: z.number().int().nonnegative(),
    citations_with_verdicts: z.number().int().nonnegative(),
    supports: z.number().int().nonnegative(),
    partly_supports: z.number().int().nonnegative(),
    does_not_support: z.number().int().nonnegative(),
    cannot_tell: z.number().int().nonnegative(),
  }),
}) satisfies z.ZodType<Schemas['ResearchQualityOut']>;

export type ResearchQuality = Schemas['ResearchQualityOut'];
export type QualityVersionGroup = Schemas['QualityVersionGroupOut'];
export type QualityJobGroup = Schemas['QualityJobGroupOut'];

export const QUALITY_WINDOWS = [7, 30, 90, 365] as const;
export type QualityWindow = (typeof QUALITY_WINDOWS)[number];

/** Administrator only; the server also requires an MFA-verified session. */
export function fetchResearchQuality(windowDays: QualityWindow): Promise<ResearchQuality> {
  return apiCall(`/api/admin/research-quality?window_days=${windowDays}`, {
    schema: researchQualitySchema,
  });
}
