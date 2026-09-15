/** Scheduled products: standing orders for reports at a fixed UTC hour. */
import { z } from 'zod';

import { scopedMutation } from '@/lib/workspaceAccess';
import type { components } from './types.gen';

import { apiCall, apiSend } from './client';

export const scheduleSchema = z.object({
  brief_id: z.uuid().nullable().optional(),
  brief_revision: z.number().int().positive().nullable().optional(),
  timezone: z.string().optional(),
  local_hour: z.number().int().min(0).max(23).optional(),
  local_minute: z.number().int().min(0).max(59).optional(),
  collection_policy: z.enum(['rolling_snapshot', 'since_last_success']).optional(),
  team_id: z.uuid().nullable(),
  anchor_month: z.number().int().min(1).max(12).default(1),
  conflict_id: z.string().nullable().default(null),
  hazard: z.string().nullable().default(null),
  research_area: z
    .object({ geometry: z.record(z.string(), z.unknown()), sha256: z.string() })
    .nullable()
    .default(null),
  disclose_area_to_provider: z.boolean().default(false),
  avoid_repetition: z.boolean().default(true),
  notify_on_change: z.boolean(),
  last_change_summary: z.string().nullable(),
  last_change: z
    .object({
      status: z.enum(['baseline', 'unchanged', 'changed', 'unavailable']),
      report_id: z.uuid(),
      version_id: z.uuid(),
      previous_report_id: z.uuid().nullable(),
      previous_version_id: z.uuid().nullable(),
      baseline_version_id: z.uuid().nullable(),
      added: z.number().int(),
      removed: z.number().int(),
      updated: z.number().int(),
      reasons: z.array(z.string()),
    })
    .nullable(),
  question: z.string().nullable(),
  research_mode: z.enum(['quick', 'detailed', 'advanced']).nullable(),
  research_languages: z.array(z.string()),
  research_focus: z.enum(['general', 'company', 'domain', 'document', 'media']),
  research_subject: z.string().nullable(),
  research_web_search: z.boolean().default(false),
  research_source_ids: z.array(z.string()).nullable().default(null),
  id: z.string(),
  name: z.string(),
  template_id: z.string(),
  country_iso: z.string().nullable(),
  country_isos: z.array(z.string()).max(8).default([]),
  plan_id: z.string().nullable(),
  hour_utc: z.number().int(),
  cadence: z.string(),
  weekday: z.number().int(),
  monthday: z.number().int().min(1).max(31).default(1),
  window_hours: z.number().int().nullable(),
  enabled: z.boolean(),
  created_by: z.string(),
  created_at: z.string(),
  next_run_at: z.string(),
  last_run_at: z.string().nullable(),
  last_report_id: z.string().nullable(),
  last_version_id: z.string().nullable().default(null),
  last_outcome: z.enum(['ready', 'needs_review', 'failed']).nullable().default(null),
  last_coverage: z.enum(['complete', 'partial', 'not_applicable']).nullable().default(null),
  last_error: z.string().nullable(),
});
export type Schedule = z.infer<typeof scheduleSchema>;

export type ScheduleRequest = components['schemas']['ScheduleIn'];

export async function fetchSchedules(signal?: AbortSignal): Promise<Schedule[]> {
  const page = await apiCall('/api/schedules', {
    schema: z.object({ items: z.array(scheduleSchema) }),
    ...(signal ? { signal } : {}),
  });
  return page.items;
}

export function createSchedule(request: ScheduleRequest): Promise<Schedule> {
  return scopedMutation(() =>
    apiCall('/api/schedules', { method: 'POST', body: request, schema: scheduleSchema }),
  );
}

export function deleteSchedule(id: string): Promise<void> {
  return scopedMutation(() =>
    apiSend(`/api/schedules/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  );
}

export function updateSchedule(id: string, request: ScheduleRequest): Promise<Schedule> {
  return scopedMutation(() =>
    apiCall(`/api/schedules/${encodeURIComponent(id)}`, {
      method: 'PUT',
      body: request,
      schema: scheduleSchema,
    }),
  );
}

export function pauseSchedule(id: string): Promise<Schedule> {
  return scopedMutation(() =>
    apiCall(`/api/schedules/${encodeURIComponent(id)}/pause`, {
      method: 'POST',
      schema: scheduleSchema,
    }),
  );
}

export function resumeSchedule(id: string): Promise<Schedule> {
  return scopedMutation(() =>
    apiCall(`/api/schedules/${encodeURIComponent(id)}/resume`, {
      method: 'POST',
      schema: scheduleSchema,
    }),
  );
}
