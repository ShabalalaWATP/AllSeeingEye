/** Administrator evaluation runs over packaged synthetic cases. Responses never carry keys. */
import { z } from 'zod';

import { apiCall, apiFile } from './client';
import type { DownloadedFile } from './client';
import type { components } from './types.gen';
import { scopedMutation } from '@/lib/workspaceAccess';

export type EvaluationCase = components['schemas']['EvaluationCaseOut'];
export type EvaluationCatalogue = components['schemas']['EvaluationCatalogueOut'];
export type EvaluationRun = components['schemas']['EvaluationRunOut'];
export type EvaluationRunStatus = components['schemas']['EvaluationRunStatus'];
export type EvaluationStopReason = components['schemas']['EvaluationStopReason'];
export type EvaluationCaseResult = components['schemas']['EvaluationCaseResultOut'];
export type EvaluationStart = components['schemas']['EvaluationStartIn'];

const base = '/api/admin/llm/evaluations';
const count = z.number().int().nonnegative();
const timestamp = z.iso.datetime({ offset: true });

const caseSchema = z.object({
  id: z.string(),
  casebook: z.enum(['core', 'regional']),
  title: z.string(),
  fingerprint: z.string(),
}) satisfies z.ZodType<EvaluationCase>;

export const evaluationCatalogueSchema = z.object({
  cases: z.array(caseSchema),
  calls_per_case: count,
  max_calls: count,
  max_cases: count,
  estimate_notice: z.string(),
  result_notice: z.string(),
}) satisfies z.ZodType<EvaluationCatalogue>;

const resultSchema = z.object({
  case_id: z.string(),
  fingerprint: z.string(),
  report_status: z.string(),
  model_calls: count,
  prompt_tokens: count.nullable(),
  completion_tokens: count.nullable(),
  checks: z.record(z.string(), z.union([z.number(), z.boolean(), z.null()])),
}) satisfies z.ZodType<EvaluationCaseResult>;

export const evaluationRunSchema = z.object({
  id: z.string(),
  profile_id: z.string(),
  profile_name: z.string(),
  model: z.string(),
  status: z.enum(['running', 'completed', 'cancelled', 'stopped']),
  stop_reason: z
    .enum([
      'call_cap',
      'allowance_limit',
      'connection_changed',
      'access_revoked',
      'interrupted',
      'failed',
    ])
    .nullable(),
  cancel_requested: z.boolean(),
  case_ids: z.array(z.string()),
  case_fingerprints: z.record(z.string(), z.string()),
  max_calls: count,
  estimated_calls: count,
  calls_reserved: count,
  calls_failed: count,
  prompt_tokens: count.nullable(),
  completion_tokens: count.nullable(),
  results: z.array(resultSchema),
  has_artefact: z.boolean(),
  created_at: timestamp,
  finished_at: timestamp.nullable(),
  notice: z.string(),
}) satisfies z.ZodType<EvaluationRun>;

const runsSchema = z.object({ items: z.array(evaluationRunSchema) });

export function fetchEvaluationCatalogue(signal?: AbortSignal): Promise<EvaluationCatalogue> {
  return apiCall(`${base}/catalogue`, {
    ...(signal ? { signal } : {}),
    schema: evaluationCatalogueSchema,
  });
}

export async function fetchEvaluationRuns(signal?: AbortSignal): Promise<EvaluationRun[]> {
  return (await apiCall(base, { ...(signal ? { signal } : {}), schema: runsSchema })).items;
}

/** Starting spends model calls, so a refreshed session must resubmit explicitly. */
export function startEvaluationRun(body: EvaluationStart): Promise<EvaluationRun> {
  return scopedMutation(() =>
    apiCall(base, {
      method: 'POST',
      body,
      schema: evaluationRunSchema,
      retryAfterRefresh: false,
    }),
  );
}

export function cancelEvaluationRun(id: string): Promise<EvaluationRun> {
  return scopedMutation(() =>
    apiCall(`${base}/${encodeURIComponent(id)}/cancel`, {
      method: 'POST',
      schema: evaluationRunSchema,
    }),
  );
}

export function downloadEvaluationArtefact(id: string): Promise<DownloadedFile> {
  return apiFile(`${base}/${encodeURIComponent(id)}/artefact`);
}
