import { z } from 'zod';
import { apiCall, apiBlob, apiSend } from './client';
import type { components } from './types.gen';
import { annotationComparisonSchema } from './annotationComparisons';
import { scopedMutation } from '@/lib/workspaceAccess';
export type AnnotationMonitor = components['schemas']['AnnotationMonitorOut'];
export type MonitorCreate = components['schemas']['AnnotationMonitorCreateIn'];
export type MonitorUpdate = components['schemas']['AnnotationMonitorUpdateIn'];
export type MonitorTransition = components['schemas']['AnnotationTransitionOut'];
const kind = z.enum(['claim', 'identity', 'relationship']);
const selection = z.object({
  report_id: z.string(),
  version_number: z.number().int().positive(),
  revisions: z
    .array(z.object({ claim_id: z.string(), revision_id: z.string() }))
    .max(20)
    .default([]),
  identity_revisions: z
    .array(z.object({ decision_id: z.string(), revision_id: z.string() }))
    .max(20)
    .default([]),
  relationship_revisions: z
    .array(z.object({ relationship_id: z.string(), revision_id: z.string() }))
    .max(20)
    .default([]),
});
export const annotationMonitorSchema = z.object({
  mode: z.enum(['selected_roots', 'report_inventory']).default('selected_roots'),
  id: z.string(),
  created_by: z.string(),
  team_id: z.string().nullable(),
  report_id: z.string(),
  version_number: z.number().int().positive(),
  name: z.string(),
  categories: z.array(kind).max(3),
  notify_on_change: z.boolean(),
  status: z.enum(['active', 'paused', 'unavailable']),
  unavailable_reason: z.string().nullable(),
  revision: z.number().int().positive(),
  checkpoint_id: z.string(),
  checkpoint_number: z.number().int().positive(),
  selection,
  created_at: z.string(),
  updated_at: z.string(),
}) satisfies z.ZodType<AnnotationMonitor>;
export const monitorTransitionSchema = z.object({
  id: z.string(),
  monitor_id: z.string(),
  checkpoint_before: z.string(),
  checkpoint_after: z.string(),
  sequence: z.number().int().positive(),
  kind: z.enum(['revision', 'rebaseline']),
  recorded_at: z.string(),
  changed_categories: z.array(kind),
  alert_id: z.string().nullable(),
  comparison_sha256: z.string().regex(/^[a-f0-9]{64}$/),
  configuration_revision: z.number().int().positive(),
  notification_categories: z.array(kind),
  notify_on_change: z.boolean(),
}) satisfies z.ZodType<MonitorTransition>;
const pagination = {
  total: z.number().int().nonnegative(),
  offset: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
};
const monitorPage = z.object({
  ...pagination,
  items: z.array(annotationMonitorSchema).max(50),
}) satisfies z.ZodType<components['schemas']['AnnotationMonitorsOut']>;
const historyPage = z.object({
  ...pagination,
  items: z.array(monitorTransitionSchema).max(50),
}) satisfies z.ZodType<components['schemas']['AnnotationTransitionsOut']>;
export const monitorTransitionDetailSchema = z.object({
  transition: monitorTransitionSchema,
  comparison: annotationComparisonSchema,
}) satisfies z.ZodType<components['schemas']['AnnotationTransitionDetailOut']>;
const path = (id: string) => `/api/annotation-monitors/${encodeURIComponent(id)}`;
const transitionPath = (id: string, transition: string) =>
  `${path(id)}/transitions/${encodeURIComponent(transition)}`;
export function listAnnotationMonitors(
  offset: number,
  signal: AbortSignal,
  scope?: { reportId: string; version: number },
) {
  const q = new URLSearchParams({ offset: String(offset), limit: '20' });
  if (scope) {
    q.set('report_id', scope.reportId);
    q.set('version_number', String(scope.version));
  }
  return apiCall(`/api/annotation-monitors?${q}`, { signal, schema: monitorPage });
}
export function fetchAnnotationMonitor(id: string, signal: AbortSignal) {
  return apiCall(path(id), { signal, schema: annotationMonitorSchema });
}
export function createAnnotationMonitor(body: MonitorCreate, signal: AbortSignal) {
  return scopedMutation(() =>
    apiCall('/api/annotation-monitors', {
      method: 'POST',
      body,
      signal,
      schema: annotationMonitorSchema,
    }),
  );
}
export function updateAnnotationMonitor(id: string, body: MonitorUpdate, signal: AbortSignal) {
  return scopedMutation(() =>
    apiCall(path(id), { method: 'PATCH', body, signal, schema: annotationMonitorSchema }),
  );
}
export function listMonitorTransitions(id: string, offset: number, signal: AbortSignal) {
  return apiCall(`${path(id)}/transitions?limit=20&offset=${offset}`, {
    signal,
    schema: historyPage,
  });
}
export function fetchMonitorTransition(id: string, transition: string, signal: AbortSignal) {
  return apiCall(transitionPath(id, transition), { signal, schema: monitorTransitionDetailSchema });
}
export function exportMonitorTransition(
  id: string,
  transition: string,
  digest: string,
  signal: AbortSignal,
) {
  const body: components['schemas']['AnnotationTransitionExportIn'] = {
    expected_comparison_sha256: digest,
  };
  return scopedMutation(() =>
    apiBlob(`${transitionPath(id, transition)}/export`, {
      method: 'POST',
      body,
      signal,
      headers: { Accept: 'application/json' },
    }),
  );
}

export function deleteAnnotationMonitor(id: string, revision: number, signal: AbortSignal) {
  return scopedMutation(() =>
    apiSend(`${path(id)}?expected_revision=${revision}`, { method: 'DELETE', signal }),
  );
}
