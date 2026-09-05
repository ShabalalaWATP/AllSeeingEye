/** A standing order for a morning INTSUM. */
import type { Schedule } from '@/lib/api/schedules';

export const schedule: Schedule = {
  id: 'e1e1e1e1-e1e1-4e1e-8e1e-e1e1e1e1e1e1',
  name: 'Morning INTSUM',
  template_id: 'intsum',
  country_iso: 'UA',
  plan_id: null,
  hour_utc: 6,
  cadence: 'daily',
  weekday: 0,
  window_hours: 24,
  enabled: true,
  created_by: '22222222-2222-4222-8222-222222222222',
  created_at: '2026-09-04T10:00:00Z',
  next_run_at: '2026-09-06T06:00:00Z',
  last_run_at: '2026-09-05T06:00:00Z',
  last_report_id: '11111111-1111-4111-8111-111111111111',
  last_error: null,
};
