/** Indicators and the alerts they raised. */
import type { Alert, Indicator } from '@/lib/api/warning';

export const indicator: Indicator = {
  id: 'c1c1c1c1-c1c1-4c1c-8c1c-c1c1c1c1c1c1',
  name: 'Kharkiv strikes',
  description: '',
  plan_id: null,
  countries: ['UA'],
  bbox: null,
  categories: ['conflict'],
  keywords: ['Kharkiv', 'shelling'],
  threshold: 2,
  window_minutes: 360,
  cooldown_minutes: 60,
  severity_floor: 0,
  report_template: 'intsum',
  enabled: true,
  created_by: '22222222-2222-4222-8222-222222222222',
  created_at: '2026-09-04T10:00:00Z',
  updated_at: '2026-09-04T10:00:00Z',
};

export const alert: Alert = {
  id: 'd1d1d1d1-d1d1-4d1d-8d1d-d1d1d1d1d1d1',
  indicator_id: indicator.id,
  fired_at: '2026-09-05T11:30:00Z',
  title: 'Kharkiv strikes: 3 items in the last 6 h',
  summary: 'Shelling in Kharkiv; Drone strike near Sumy; Strike on a depot',
  count: 3,
  threshold: 2,
  event_ids: ['k1', 'k2', 'k3'],
  countries: ['UA'],
  acknowledged_at: null,
  acknowledged_by: null,
  report_id: '11111111-1111-4111-8111-111111111111',
};

export const acknowledgedAlert: Alert = {
  ...alert,
  id: 'd2d2d2d2-d2d2-4d2d-8d2d-d2d2d2d2d2d2',
  fired_at: '2026-09-04T22:00:00Z',
  title: 'Kharkiv strikes: 2 items in the last 6 h',
  count: 2,
  acknowledged_at: '2026-09-04T22:10:00Z',
  acknowledged_by: '22222222-2222-4222-8222-222222222222',
  report_id: null,
};
