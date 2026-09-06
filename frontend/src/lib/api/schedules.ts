/** Scheduled products: standing orders for reports at a fixed UTC hour. */
import { z } from 'zod';

import { scopedMutation } from '@/lib/workspaceAccess';
import type { components } from './types.gen';

import { apiCall, apiSend } from './client';

export const scheduleSchema = z.object({
  team_id: z.uuid().nullable(),
  id: z.string(),
  name: z.string(),
  template_id: z.string(),
  country_iso: z.string().nullable(),
  plan_id: z.string().nullable(),
  hour_utc: z.number().int(),
  cadence: z.string(),
  weekday: z.number().int(),
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
