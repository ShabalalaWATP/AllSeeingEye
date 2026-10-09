/** Warning: indicators over the live picture and the alerts they raise. */
import { z } from 'zod';
import { frozenAreaSchema } from './areaSchemas';
import type { OwnershipScope } from '@/lib/ownershipScope';

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
  research_area: frozenAreaSchema.nullable().optional(),
  categories: z.array(z.string()),
  keywords: z.array(z.string()),
  threshold: z.number().int(),
  baseline_ratio: z.number().nullable().optional(),
  baseline_days: z.number().int().optional(),
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
  annotation_monitor_id: z.string().nullable().default(null),
  annotation_transition_id: z.string().nullable().default(null),
  team_id: z.uuid().nullable(),
  id: z.string(),
  indicator_id: z.string().nullable(),
  schedule_id: z.string().nullable(),
  fired_at: z.string(),
  title: z.string(),
  summary: z.string(),
  count: z.number().int(),
  threshold: z.number().int(),
  event_ids: z.array(z.string()),
  countries: z.array(z.string()),
  acknowledged_at: z.string().nullable(),
  acknowledged_by: z.string().nullable(),
  disposition: z.enum(['useful', 'noise', 'duplicate']).nullable().optional(),
  disposition_note: z.string().nullable().optional(),
  baseline_mean: z.number().nullable().optional(),
  baseline_ratio: z.number().nullable().optional(),
  report_id: z.string().nullable(),
  report_job_id: z.string().nullable().optional(),
  report_status: z
    .enum([
      'pending',
      'queued',
      'running',
      'paused',
      'failed',
      'completed',
      'needs_review',
      'cancelled',
      'discarded',
    ])
    .nullable()
    .optional(),
  report_error: z.string().nullable().optional(),
  created_by: z.string().nullable().default(null),
  owner_name: z.string().nullable().default(null),
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

export function updateIndicator(
  id: string,
  request: components['schemas']['IndicatorUpdateIn'],
): Promise<Indicator> {
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

export function fetchAlerts(
  hours?: number,
  signal?: AbortSignal,
  scope: OwnershipScope = 'mine',
): Promise<AlertsPage> {
  const params = new URLSearchParams();
  if (hours !== undefined) params.set('hours', String(hours));
  if (scope === 'all') params.set('scope', 'all');
  const query = params.toString();
  return apiCall(`/api/warning/alerts${query ? `?${query}` : ''}`, {
    schema: alertsPageSchema,
    ...(signal ? { signal } : {}),
  });
}

export type AlertAcknowledgementRequest = components['schemas']['AlertAcknowledgementIn'];

export function acknowledgeAlert(
  id: string,
  feedback?: AlertAcknowledgementRequest,
): Promise<Alert> {
  return scopedMutation(() =>
    apiCall(`/api/warning/alerts/${encodeURIComponent(id)}/ack`, {
      method: 'POST',
      body: feedback,
      schema: alertSchema,
    }),
  );
}

export function fetchAlertFeedback(id: string) {
  return apiCall(`/api/warning/indicators/${encodeURIComponent(id)}/feedback`, {
    schema: z.object({
      indicator_id: z.uuid(),
      since: z.string(),
      until: z.string(),
      useful: z.number().int().nonnegative(),
      noise: z.number().int().nonnegative(),
      duplicate: z.number().int().nonnegative(),
      time_basis: z.string(),
    }),
  });
}

export function fetchIndicatorBaseline(id: string) {
  return apiCall(`/api/warning/indicators/${encodeURIComponent(id)}/baseline`, {
    schema: z.object({
      sample_hours: z.number().int().nonnegative(),
      mean: z.number().nullable(),
      earliest: z.string().nullable(),
      as_of: z.string(),
      ready: z.boolean(),
      reason: z.string(),
    }),
  });
}
