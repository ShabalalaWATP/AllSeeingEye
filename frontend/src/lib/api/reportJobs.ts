import { z } from 'zod';
import type { components } from './types.gen';
import { apiCall, apiSend } from './client';
import { ApiError } from './errors';
import { scopedMutation } from '@/lib/workspaceAccess';
import { researchUsageMutation } from '@/lib/researchUsageEvents';

export type ReportJob = components['schemas']['ReportJobOut'];
export type ReportJobCreate = components['schemas']['ReportJobCreateIn'];
export type ReportJobSection = components['schemas']['ReportJobSectionOut'];

export const reportJobSchema: z.ZodType<ReportJob> = z.object({
  id: z.uuid(),
  revision: z.number().int().positive(),
  title: z.string(),
  status: z.enum(['queued', 'running', 'paused', 'completed', 'needs_review', 'failed']),
  stage: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  team_id: z.uuid().nullable(),
  report_id: z.uuid().nullable(),
  model: z.string(),
  reasoning_effort: z.string().nullable(),
  error: z.string().nullable(),
  can_resume: z.boolean(),
  completed_sections: z.number().int().nonnegative(),
  total_sections: z.number().int().nonnegative(),
  sections: z.array(
    z.object({
      id: z.string(),
      title: z.string(),
      kind: z.enum(['topic', 'synthesis']),
      status: z.enum(['running', 'completed', 'split', 'incomplete']),
      reporting: z.array(z.string()).default([]),
      assessment: z.string().nullable(),
      gaps: z.array(z.string()).default([]),
      citations: z.array(z.string()).default([]),
      error: z.string().nullable(),
    }),
  ),
  usage: z.object({
    calls: z.number().int().nonnegative(),
    max_calls: z.number().int().nonnegative(),
    output_tokens: z.number().int().nonnegative(),
    output_allowance: z.number().int().nonnegative(),
    uncertain_calls: z.number().int().nonnegative(),
  }),
});

export function createReportJob(body: ReportJobCreate, signal: AbortSignal) {
  return researchUsageMutation(() =>
    apiCall('/api/report-jobs', {
      method: 'POST',
      body,
      schema: reportJobSchema,
      signal,
      retryAfterRefresh: false,
    }),
  );
}
export async function fetchReportJobs(signal: AbortSignal) {
  const page = await apiCall('/api/report-jobs?limit=20', {
    schema: z.object({ items: z.array(reportJobSchema) }),
    signal,
  });
  return page.items;
}
function matchingJob(job: ReportJob, id: string) {
  if (job.id !== id)
    throw new ApiError(
      502,
      'invalid_response',
      'The server returned a different research job. Refresh the job list.',
    );
  return job;
}
export async function fetchReportJob(id: string, signal: AbortSignal) {
  return matchingJob(
    await apiCall(`/api/report-jobs/${encodeURIComponent(id)}`, {
      schema: reportJobSchema,
      signal,
    }),
    id,
  );
}
export function controlReportJob(id: string, action: 'pause' | 'resume', signal: AbortSignal) {
  return scopedMutation(async () =>
    matchingJob(
      await apiCall(`/api/report-jobs/${encodeURIComponent(id)}/${action}`, {
        method: 'POST',
        schema: reportJobSchema,
        signal,
        retryAfterRefresh: false,
      }),
      id,
    ),
  );
}
export function discardReportJob(id: string, signal: AbortSignal) {
  return scopedMutation(() =>
    apiSend(`/api/report-jobs/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      signal,
      retryAfterRefresh: false,
    }),
  );
}
