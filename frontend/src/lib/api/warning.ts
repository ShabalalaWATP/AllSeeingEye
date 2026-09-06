/** Warning: indicators over the live picture and the alerts they raise. */
import { z } from 'zod';

import { scopedMutation } from '@/lib/workspaceAccess';
import type { components } from './types.gen';

import { apiCall, apiSend } from './client';

export const indicatorSchema = z.object({
  team_id: z.uuid().nullable(),
  id: z.string(),
  name: z.string(),
  description: z.string(),
  plan_id: z.string().nullable(),
  countries: z.array(z.string()),
  bbox: z.array(z.number()).nullable(),
  categories: z.array(z.string()),
  keywords: z.array(z.string()),
  threshold: z.number().int(),
  window_minutes: z.number().int(),
  cooldown_minutes: z.number().int(),
  severity_floor: z.number(),
  report_template: z.string().nullable(),
  enabled: z.boolean(),
  created_by: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type Indicator = z.infer<typeof indicatorSchema>;

export const alertSchema = z.object({
  team_id: z.uuid().nullable(),
  id: z.string(),
  indicator_id: z.string(),
  fired_at: z.string(),
  title: z.string(),
  summary: z.string(),
  count: z.number().int(),
  threshold: z.number().int(),
  event_ids: z.array(z.string()),
  countries: z.array(z.string()),
  acknowledged_at: z.string().nullable(),
  acknowledged_by: z.string().nullable(),
  report_id: z.string().nullable(),
});
export type Alert = z.infer<typeof alertSchema>;

export const alertsPageSchema = z.object({
  items: z.array(alertSchema),
  unacknowledged: z.number().int(),
});
export type AlertsPage = z.infer<typeof alertsPageSchema>;

export type IndicatorRequest = components['schemas']['IndicatorIn'];

export async function fetchIndicators(): Promise<Indicator[]> {
  const page = await apiCall('/api/warning/indicators', {
    schema: z.object({ items: z.array(indicatorSchema) }),
  });
  return page.items;
}

export function createIndicator(request: IndicatorRequest): Promise<Indicator> {
  return scopedMutation(() =>
    apiCall('/api/warning/indicators', {
      method: 'POST',
      body: request,
      schema: indicatorSchema,
    }),
  );
}

export function updateIndicator(id: string, request: IndicatorRequest): Promise<Indicator> {
  return scopedMutation(() =>
    apiCall(`/api/warning/indicators/${encodeURIComponent(id)}`, {
      method: 'PUT',
      body: request,
      schema: indicatorSchema,
    }),
  );
}

export function deleteIndicator(id: string): Promise<void> {
  return scopedMutation(() =>
    apiSend(`/api/warning/indicators/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  );
}

export function fetchAlerts(hours?: number): Promise<AlertsPage> {
  const query = hours === undefined ? '' : `?hours=${String(hours)}`;
  return apiCall(`/api/warning/alerts${query}`, { schema: alertsPageSchema });
}

export function acknowledgeAlert(id: string): Promise<Alert> {
  return scopedMutation(() =>
    apiCall(`/api/warning/alerts/${encodeURIComponent(id)}/ack`, {
      method: 'POST',
      schema: alertSchema,
    }),
  );
}
