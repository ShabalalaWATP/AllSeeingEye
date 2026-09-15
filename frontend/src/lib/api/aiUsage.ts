import { z } from 'zod';

import { apiCall, apiSend } from './client';

export type AiScope = 'global' | 'user' | 'team';
export type AiPeriod = 'day' | 'week' | 'month';

export interface AiPolicy {
  id: string;
  scope: AiScope;
  target_id: string | null;
  period: AiPeriod;
  request_limit: number | null;
  token_limit: number | null;
  enabled: boolean;
  revision: number;
  created_at: string;
  updated_at: string;
}

export interface AiUsageSummary {
  policy: AiPolicy;
  period_start: string;
  period_end: string;
  used_requests: number;
  reserved_requests: number;
  remaining_requests: number | null;
  used_tokens: number;
  reserved_tokens: number;
  remaining_tokens: number | null;
}

const policySchema: z.ZodType<AiPolicy> = z.object({
  id: z.uuid(),
  scope: z.enum(['global', 'user', 'team']),
  target_id: z.uuid().nullable(),
  period: z.enum(['day', 'week', 'month']),
  request_limit: z.number().int().nonnegative().nullable(),
  token_limit: z.number().int().nonnegative().nullable(),
  enabled: z.boolean(),
  revision: z.number().int().min(1),
  created_at: z.string(),
  updated_at: z.string(),
});
const policiesSchema = z.array(policySchema);
const summarySchema: z.ZodType<AiUsageSummary> = z.object({
  policy: policySchema,
  period_start: z.string(),
  period_end: z.string(),
  used_requests: z.number().int().nonnegative(),
  reserved_requests: z.number().int().nonnegative(),
  remaining_requests: z.number().int().nonnegative().nullable(),
  used_tokens: z.number().int().nonnegative(),
  reserved_tokens: z.number().int().nonnegative(),
  remaining_tokens: z.number().int().nonnegative().nullable(),
});
const summariesSchema = z.object({ items: z.array(summarySchema) });

export interface AiPolicyInput {
  scope: AiScope;
  target_id?: string | null;
  period: AiPeriod;
  request_limit: number | null;
  token_limit: number | null;
  enabled: boolean;
}

export function listAiPolicies(): Promise<AiPolicy[]> {
  return apiCall('/api/admin/ai-usage/policies', { schema: policiesSchema });
}

export function createAiPolicy(body: AiPolicyInput): Promise<AiPolicy> {
  return apiCall('/api/admin/ai-usage/policies', { method: 'POST', body, schema: policySchema });
}

export function updateAiPolicy(id: string, body: AiPolicyInput): Promise<AiPolicy> {
  return apiCall(`/api/admin/ai-usage/policies/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body,
    schema: policySchema,
  });
}

export function disableAiPolicy(id: string): Promise<void> {
  return apiSend(`/api/admin/ai-usage/policies/${encodeURIComponent(id)}`, { method: 'DELETE' });
}

export function getMyAiUsage(): Promise<AiUsageSummary[]> {
  return apiCall('/api/ai-usage/me', { schema: summariesSchema }).then((page) => page.items);
}

export function getTeamAiUsage(teamId: string): Promise<AiUsageSummary[]> {
  return apiCall(`/api/teams/${encodeURIComponent(teamId)}/ai-usage`, {
    schema: summariesSchema,
  }).then((page) => page.items);
}

export function previewAiUsage(userId: string, teamId?: string): Promise<AiUsageSummary[]> {
  const params = new URLSearchParams({ user_id: userId });
  if (teamId) params.set('team_id', teamId);
  return apiCall(`/api/admin/ai-usage/preview?${params.toString()}`, {
    schema: summariesSchema,
  }).then((page) => page.items);
}
