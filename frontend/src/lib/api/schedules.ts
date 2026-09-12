/** Scheduled products: standing orders for reports at a fixed UTC hour. */
import { z } from 'zod';

import { scopedMutation } from '@/lib/workspaceAccess';
import type { components } from './types.gen';

import { apiCall, apiSend } from './client';

export const scheduleSchema = z.object({
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
  last_error: z.string().nullable(),
});
export type Schedule = z.infer<typeof scheduleSchema>;

export type ScheduleRequest = components['schemas']['ScheduleIn'];

export async function fetchSchedules(): Promise<Schedule[]> {
  const page = await apiCall('/api/schedules', {
    schema: z.object({ items: z.array(scheduleSchema) }),
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

/** PUT is a full replacement. Preserve every saved option when changing run status. */
export function scheduleRequest(schedule: Schedule, enabled: boolean): ScheduleRequest {
  return {
    name: schedule.name,
    anchor_month: schedule.anchor_month,
    conflict_id: schedule.conflict_id,
    hazard: schedule.hazard,
    research_area: schedule.research_area ? { geometry: schedule.research_area.geometry } : null,
    disclose_area_to_provider: schedule.disclose_area_to_provider,
    avoid_repetition: schedule.avoid_repetition,
    template_id: schedule.template_id,
    country_iso: schedule.country_iso,
    country_isos: schedule.country_isos,
    plan_id: schedule.plan_id,
    team_id: schedule.team_id,
    hour_utc: schedule.hour_utc,
    cadence: schedule.cadence,
    weekday: schedule.weekday,
    monthday: schedule.monthday,
    window_hours: schedule.window_hours,
    enabled,
    notify_on_change: schedule.notify_on_change,
    question: schedule.question,
    research_mode: schedule.research_mode,
    research_languages: schedule.research_languages,
    research_focus: schedule.research_focus,
    research_subject: schedule.research_subject,
    research_web_search: schedule.research_web_search,
    research_source_ids: schedule.research_source_ids,
  };
}
