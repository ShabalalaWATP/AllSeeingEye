/** Scheduled products: standing orders for reports at a fixed UTC hour. */
import { z } from 'zod';

import { apiCall, apiSend } from './client';

export const scheduleSchema = z.object({
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

export interface ScheduleRequest {
  name: string;
  template_id: string;
  country_iso?: string | null;
  plan_id?: string | null;
  hour_utc?: number;
  cadence?: 'daily' | 'weekdays' | 'weekly';
  weekday?: number;
  window_hours?: number | null;
  enabled?: boolean;
}

export async function fetchSchedules(): Promise<Schedule[]> {
  const page = await apiCall('/api/schedules', {
    schema: z.object({ items: z.array(scheduleSchema) }),
  });
  return page.items;
}

export function createSchedule(request: ScheduleRequest): Promise<Schedule> {
  return apiCall('/api/schedules', { method: 'POST', body: request, schema: scheduleSchema });
}

export function deleteSchedule(id: string): Promise<void> {
  return apiSend(`/api/schedules/${encodeURIComponent(id)}`, { method: 'DELETE' });
}
