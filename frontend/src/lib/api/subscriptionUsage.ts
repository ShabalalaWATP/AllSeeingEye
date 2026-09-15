/** Server-accounted UTC-month report allowances; token counts are not currency estimates. */
import { z } from 'zod';

import { apiCall } from './client';

const countsSchema = z.object({
  requests: z.number().int().nonnegative(),
  output_tokens: z.number().int().nonnegative(),
});

const usageSchema = z.object({
  scope: z.enum(['owner', 'subscription']),
  subscription_id: z.uuid().nullable(),
  month_start: z.string(),
  month_end: z.string(),
  policy_version: z.string(),
  used: countsSchema,
  limit: countsSchema,
});

export type MonthlyUsage = z.infer<typeof usageSchema>;

export function fetchOwnerMonthlyUsage(): Promise<MonthlyUsage> {
  return apiCall('/api/schedules/usage', { schema: usageSchema });
}

export function fetchSubscriptionMonthlyUsage(id: string): Promise<MonthlyUsage> {
  return apiCall(`/api/schedules/${encodeURIComponent(id)}/usage`, { schema: usageSchema });
}
