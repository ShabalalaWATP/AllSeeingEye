import { z } from 'zod';

import { scopedMutation } from '@/lib/workspaceAccess';
import { apiCall } from './client';
import type { ResearchBrief } from './researchBriefSchema';
import { scheduleSchema } from './schedules';

export const briefSubscriptionSettingsSchema = z.object({
  name: z.string().min(1).max(120),
  timezone: z.string().min(1).max(100),
  local_hour: z.number().int().min(0).max(23),
  local_minute: z.number().int().min(0).max(59),
  cadence: z.enum(['daily', 'weekdays', 'weekly', 'monthly', 'quarterly', 'semiannual', 'annual']),
  weekday: z.number().int().min(0).max(6),
  monthday: z.number().int().min(1).max(31),
  anchor_month: z.number().int().min(1).max(12),
  collection_policy: z.enum(['rolling_snapshot', 'since_last_success']),
  enabled: z.boolean(),
  notify_on_change: z.boolean(),
  avoid_repetition: z.boolean(),
});
export type BriefSubscriptionSettings = z.infer<typeof briefSubscriptionSettingsSchema>;

const briefScheduleSchema = scheduleSchema.extend({
  brief_id: z.uuid(),
  brief_revision: z.number().int().positive(),
});

export function createBriefSubscription(
  brief: ResearchBrief,
  settings: BriefSubscriptionSettings,
  signal: AbortSignal,
) {
  const body = {
    brief_id: brief.identity.id,
    brief_revision: brief.identity.revision,
    ...briefSubscriptionSettingsSchema.parse(settings),
  };
  return scopedMutation(() =>
    apiCall('/api/schedules/from-brief', {
      method: 'POST',
      body,
      schema: briefScheduleSchema,
      signal,
      retryAfterRefresh: false,
    }),
  );
}
