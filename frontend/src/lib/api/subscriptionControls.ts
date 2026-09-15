import { z } from 'zod';

import { scopedMutation } from '@/lib/workspaceAccess';

import { apiCall } from './client';
import { subscriptionEditionSchema } from './subscriptionEditions';

const eventSchema = z.object({
  id: z.uuid(),
  edition_id: z.uuid(),
  event_kind: z.string(),
  created_at: z.string(),
});

const eventsPageSchema = z.object({
  items: z.array(eventSchema),
  limit: z.number().int(),
  offset: z.number().int(),
});

const baselineSchema = z.object({
  subscription_id: z.uuid(),
  edition_id: z.uuid(),
  analytical_baseline_version_id: z.uuid(),
  covered_intervals: z.array(z.object({ start: z.string(), end: z.string() })),
  complete_cutoff: z.string().nullable(),
});

export type SubscriptionEvent = z.infer<typeof eventSchema>;
export type EditionControl = 'pause' | 'resume' | 'retry';

export function runSubscriptionNow(subscriptionId: string, requestId: string) {
  return scopedMutation(() =>
    apiCall(`/api/schedules/${encodeURIComponent(subscriptionId)}/run-now`, {
      method: 'POST',
      body: { request_id: requestId },
      retryAfterRefresh: false,
      schema: subscriptionEditionSchema,
    }),
  );
}

export function controlSubscriptionEdition(
  subscriptionId: string,
  editionId: string,
  action: EditionControl,
) {
  return scopedMutation(() =>
    apiCall(
      `/api/schedules/${encodeURIComponent(subscriptionId)}/editions/${encodeURIComponent(editionId)}/${action}`,
      { method: 'POST', schema: subscriptionEditionSchema },
    ),
  );
}

export function acceptSubscriptionBaseline(subscriptionId: string, editionId: string) {
  return scopedMutation(() =>
    apiCall(
      `/api/schedules/${encodeURIComponent(subscriptionId)}/editions/${encodeURIComponent(editionId)}/accept-baseline`,
      { method: 'POST', schema: baselineSchema },
    ),
  );
}

export function fetchSubscriptionEvents(subscriptionId: string, signal?: AbortSignal) {
  return apiCall(`/api/schedules/${encodeURIComponent(subscriptionId)}/events?limit=10`, {
    schema: eventsPageSchema,
    ...(signal ? { signal } : {}),
  });
}
