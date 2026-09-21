/** Research runs are separate from the model calls made inside each run. */
import { z } from 'zod';

import { invalidateResearchUsage } from '@/lib/researchUsageEvents';
import { scopedMutation } from '@/lib/workspaceAccess';

import { apiCall } from './client';
import type { components } from './types.gen';

type Schemas = components['schemas'];
export type ResearchAllowance = Schemas['ResearchAllowanceOut'];
export type ResearchUsagePage = Schemas['ResearchUsagePageOut'];
export type UserResearchAllowance = Schemas['UserResearchAllowanceOut'];
export type ResearchTierInput = Schemas['ResearchTierIn'];

export const researchTierSchema = z.union([z.literal(1), z.literal(2), z.literal(3), z.literal(4)]);
const period = z.enum(['day', 'week']);
const count = z.number().int().nonnegative();
const tierSchema = z.object({
  tier: researchTierSchema,
  label: z.string(),
  limit: z.number().int().positive(),
  period,
});
const allowanceSchema = tierSchema.extend({
  used: count,
  remaining: count,
  period_start: z.string(),
  resets_at: z.string(),
  revision: count,
}) satisfies z.ZodType<ResearchAllowance>;
const userAllowanceSchema = allowanceSchema.extend({
  user_id: z.uuid(),
}) satisfies z.ZodType<UserResearchAllowance>;
const pageSchema = z.object({
  tiers: z.array(tierSchema),
  items: z.array(userAllowanceSchema),
}) satisfies z.ZodType<ResearchUsagePage>;

export function getMyResearchUsage(): Promise<ResearchAllowance> {
  return apiCall('/api/research-usage/me', { schema: allowanceSchema });
}

export function getAdminResearchUsage(): Promise<ResearchUsagePage> {
  return apiCall('/api/admin/research-usage', { schema: pageSchema });
}

export async function setUserResearchTier(
  userId: string,
  body: ResearchTierInput,
): Promise<UserResearchAllowance> {
  const result = await scopedMutation(() =>
    apiCall(`/api/admin/users/${encodeURIComponent(userId)}/research-tier`, {
      method: 'PUT',
      body,
      schema: userAllowanceSchema,
      retryAfterRefresh: false,
    }),
  );
  invalidateResearchUsage();
  return result;
}
