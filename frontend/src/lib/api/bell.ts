/** The in-app notification bell: scoped summary, destinations, acknowledgement and mutes. */
import { z } from 'zod';

import { scopedMutation } from '@/lib/workspaceAccess';

import { apiCall } from './client';
import type { components } from './types.gen';

export type Bell = components['schemas']['BellOut'];
export type BellAlert = components['schemas']['BellAlertOut'];
export type BellKind = components['schemas']['BellKind'];
export type BellPreferences = components['schemas']['BellPreferencesOut'];
export type AlertDestination = components['schemas']['AlertDestinationOut'];
export type BellAcknowledgement = components['schemas']['BellAcknowledgeOut'];
export type BellMention = components['schemas']['BellMentionOut'];
export type MentionOpen = components['schemas']['MentionOpenOut'];

/** The most alerts one "Acknowledge shown" request may name. */
export const MAX_ACKNOWLEDGE_BATCH = 20;

const kind = z.enum(['alerts', 'research', 'mentions']) satisfies z.ZodType<BellKind>;
const alertSchema = z.object({
  id: z.uuid(),
  title: z.string(),
  summary: z.string(),
  fired_at: z.string(),
  indicator_id: z.uuid().nullable(),
  report_id: z.uuid().nullable(),
  annotation_monitor_id: z.uuid().nullable(),
  team_id: z.uuid().nullable(),
  team_name: z.string().nullable(),
  can_acknowledge: z.boolean(),
}) satisfies z.ZodType<BellAlert>;
const preferencesSchema = z.object({
  muted_kinds: z.array(kind),
  muted_rules: z.array(
    z.object({ indicator_id: z.uuid(), name: z.string(), muted_at: z.string() }),
  ),
}) satisfies z.ZodType<BellPreferences>;
const mentionSchema = z.object({
  post_id: z.uuid(),
  thread_id: z.uuid(),
  team_id: z.uuid(),
  team_name: z.string(),
  author_name: z.string(),
  snippet: z.string(),
  created_at: z.string(),
}) satisfies z.ZodType<BellMention>;
const bellSchema = z.object({
  window_days: z.number().int().positive(),
  alerts: z.object({
    items: z.array(alertSchema),
    total: z.number().int().nonnegative(),
    muted: z.boolean(),
  }),
  mentions: z.object({
    items: z.array(mentionSchema),
    unread: z.number().int().nonnegative(),
    muted: z.boolean(),
  }),
  preferences: preferencesSchema,
}) satisfies z.ZodType<Bell>;
const openSchema = z.object({
  team_id: z.uuid(),
  post_id: z.uuid(),
  thread_id: z.uuid(),
}) satisfies z.ZodType<MentionOpen>;
const destinationSchema = z.object({
  kind: z.enum(['report', 'transition', 'alerts']),
  available: z.boolean(),
  report_id: z.uuid().nullable(),
  monitor_id: z.uuid().nullable(),
  transition_id: z.uuid().nullable(),
  message: z.string().nullable(),
}) satisfies z.ZodType<AlertDestination>;
const acknowledgementSchema = z.object({
  acknowledged: z.array(z.uuid()),
  failed: z.array(z.object({ alert_id: z.uuid(), message: z.string() })),
}) satisfies z.ZodType<BellAcknowledgement>;

const id = (value: string) => encodeURIComponent(value);

export function fetchBell(signal?: AbortSignal): Promise<Bell> {
  return apiCall('/api/bell', { schema: bellSchema, ...(signal ? { signal } : {}) });
}

/** Re-checks the alert and where it leads against the caller's current access. */
export function fetchAlertDestination(alertId: string): Promise<AlertDestination> {
  return apiCall(`/api/bell/alerts/${id(alertId)}/destination`, { schema: destinationSchema });
}

/** Acknowledges exactly these alert IDs; each is authorised on its own. */
export function acknowledgeAlerts(alertIds: readonly string[]): Promise<BellAcknowledgement> {
  return scopedMutation(() =>
    apiCall('/api/bell/alerts/acknowledge', {
      method: 'POST',
      body: { alert_ids: alertIds },
      schema: acknowledgementSchema,
    }),
  );
}

export function setMutedKinds(kinds: readonly BellKind[]): Promise<BellPreferences> {
  return apiCall('/api/bell/preferences', {
    method: 'PUT',
    body: { muted_kinds: kinds },
    schema: preferencesSchema,
  });
}

export function muteRule(indicatorId: string): Promise<BellPreferences> {
  return scopedMutation(() =>
    apiCall(`/api/bell/muted-rules/${id(indicatorId)}`, {
      method: 'PUT',
      schema: preferencesSchema,
    }),
  );
}

export function unmuteRule(indicatorId: string): Promise<BellPreferences> {
  return apiCall(`/api/bell/muted-rules/${id(indicatorId)}`, {
    method: 'DELETE',
    schema: preferencesSchema,
  });
}

/** Re-checks the post against current membership and marks this account's mention read. */
export function openMention(postId: string): Promise<MentionOpen> {
  // A 404 here usually means the post was removed, not that workspace access changed.
  return apiCall(`/api/bell/mentions/${id(postId)}/open`, { method: 'POST', schema: openSchema });
}

/** Marks only this account's own mentions read; returns its remaining unread count. */
export function markMentionsRead(postIds: readonly string[]): Promise<number> {
  return apiCall('/api/bell/mentions/read', {
    method: 'POST',
    body: { post_ids: postIds },
    schema: z.object({ unread: z.number().int().nonnegative() }),
  }).then((result) => result.unread);
}
