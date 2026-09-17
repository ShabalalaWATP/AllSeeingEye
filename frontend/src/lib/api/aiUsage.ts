/** AI allowance contracts come from OpenAPI; responses are validated before rendering. */
import { z } from 'zod';

import { apiCall, apiSend } from './client';
import type { components } from './types.gen';

type Schemas = components['schemas'];
export type AiScope = Schemas['AiPolicyScope'];
export type AiPeriod = Schemas['AiAllowancePeriod'];
export type AiLimitState = Schemas['AiLimitState'];
export type AiPolicy = Schemas['AiUsagePolicyOut'];
export type AiPolicyInput = Schemas['AiUsagePolicyIn'];
export type AiOverride = Schemas['AiPolicyOverrideOut'];
export type AiOverrideInput = Schemas['AiPolicyOverrideIn'];
export type AiUsageSummary = Schemas['AiUsageSummaryOut'];
export type AiUsageTotals = Schemas['AiUsageTotalsOut'];
export type AiUsagePage = Schemas['AiUsageSummaryPageOut'];
export type AiUsagePreview = Schemas['AiUsagePreviewOut'];
export type TeamAiUsage = Schemas['TeamAiUsageOut'];
export type AiTokenPrices = Schemas['AiTokenPricesOut'];
export type AiEffectiveModel = Schemas['AiEffectiveModelOut'];
export type AiPolicyDefaults = Schemas['AiPolicyDefaultsOut'];
export type AiSuggestedPolicy = Schemas['SuggestedPolicyOut'];

const count = z.number().int().nonnegative();
const limit = count.nullable();
const scopeSchema = z.enum(['global', 'system', 'user', 'team']) satisfies z.ZodType<AiScope>;
const periodSchema = z.enum(['day', 'week', 'month']) satisfies z.ZodType<AiPeriod>;
const stateSchema = z.enum([
  'inherit',
  'limit',
  'unlimited',
  'blocked',
]) satisfies z.ZodType<AiLimitState>;

const policySchema = z.object({
  id: z.uuid(),
  scope: scopeSchema,
  target_id: z.uuid().nullable(),
  period: periodSchema,
  request_limit: limit,
  token_limit: limit,
  enabled: z.boolean(),
  revision: z.number().int().min(1),
  created_at: z.string(),
  updated_at: z.string(),
}) satisfies z.ZodType<AiPolicy>;
const policiesSchema = z.array(policySchema);

const limitOverrideSchema = z.object({ state: stateSchema, value: limit }) satisfies z.ZodType<
  Schemas['AiLimitOverrideOut']
>;
const overrideSchema = z.object({
  id: z.uuid(),
  policy_id: z.uuid(),
  requests: limitOverrideSchema,
  tokens: limitOverrideSchema,
  effective_from: z.string(),
  expires_at: z.string(),
  created_by: z.uuid(),
  created_at: z.string(),
  revoked_at: z.string().nullable(),
}) satisfies z.ZodType<AiOverride>;
const overridesSchema = z.object({ items: z.array(overrideSchema) }) satisfies z.ZodType<
  Schemas['AiPolicyOverridesOut']
>;

const summarySchema = z.object({
  policy: policySchema,
  period_start: z.string(),
  period_end: z.string(),
  request_limit: limit,
  token_limit: limit,
  override: overrideSchema.nullable(),
  used_requests: count,
  reserved_requests: count,
  remaining_requests: limit,
  used_tokens: count,
  reserved_tokens: count,
  remaining_tokens: limit,
}) satisfies z.ZodType<AiUsageSummary>;
const totalsSchema = z.object({
  period_start: z.string(),
  period_end: z.string(),
  used_requests: count,
  used_tokens: count,
  unknown_requests: count,
  used_input_tokens: count,
  used_output_tokens: count,
  estimated_cost: z.string().nullable(),
}) satisfies z.ZodType<AiUsageTotals>;
const pricesSchema = z.object({
  input_per_million: z.number().nonnegative(),
  output_per_million: z.number().nonnegative(),
  currency: z.string(),
  configured: z.boolean(),
}) satisfies z.ZodType<AiTokenPrices>;
const effortSchema = z.enum([
  'none',
  'minimal',
  'low',
  'medium',
  'high',
  'xhigh',
  'max',
]) satisfies z.ZodType<NonNullable<AiEffectiveModel['reasoning_effort']>>;
const modelSchema = z.object({
  policy: z.enum(['legacy', 'global', 'team', 'personal']).nullable(),
  profile_id: z.uuid().nullable(),
  profile_name: z.string(),
  model: z.string(),
  provider: z.enum(['openai_compatible', 'bedrock']).nullable(),
  reasoning_effort: effortSchema.nullable(),
  mechanical_effort: effortSchema.nullable(),
  unavailable: z.string().nullable(),
}) satisfies z.ZodType<AiEffectiveModel>;
const pageSchema = z.object({
  items: z.array(summarySchema),
  observed: totalsSchema,
  prices: pricesSchema,
}) satisfies z.ZodType<AiUsagePage>;
const previewSchema = z.object({
  items: z.array(summarySchema),
  observed: totalsSchema,
  unknown_calls: count,
  prices: pricesSchema,
  model: modelSchema.nullable(),
}) satisfies z.ZodType<AiUsagePreview>;
const suggestionSchema = z.object({
  scope: scopeSchema,
  target_id: z.uuid().nullable(),
  target_name: z.string(),
  period: periodSchema,
  token_limit: count,
  reason: z.string(),
  already_configured: z.boolean(),
}) satisfies z.ZodType<AiSuggestedPolicy>;
const defaultsSchema = z.object({
  items: z.array(suggestionSchema),
  observed: totalsSchema,
  observed_daily_tokens: count,
  enforcing: z.boolean(),
  prices: pricesSchema,
}) satisfies z.ZodType<AiPolicyDefaults>;
const appliedSchema = z.object({ created: z.array(policySchema) });
const teamSchema = z.object({
  team_id: z.uuid(),
  view: z.enum(['member', 'manager', 'admin']),
  items: z.array(summarySchema),
  own: totalsSchema,
  team: totalsSchema.nullable(),
  members: z
    .array(z.object({ user_id: z.uuid(), display_name: z.string(), observed: totalsSchema }))
    .nullable(),
  prices: pricesSchema,
}) satisfies z.ZodType<TeamAiUsage>;

const policyPath = (id: string) => `/api/admin/ai-usage/policies/${encodeURIComponent(id)}`;

export function listAiPolicies(): Promise<AiPolicy[]> {
  return apiCall('/api/admin/ai-usage/policies', { schema: policiesSchema });
}

export function createAiPolicy(body: AiPolicyInput): Promise<AiPolicy> {
  return apiCall('/api/admin/ai-usage/policies', { method: 'POST', body, schema: policySchema });
}

export function updateAiPolicy(id: string, body: AiPolicyInput): Promise<AiPolicy> {
  return apiCall(policyPath(id), { method: 'PUT', body, schema: policySchema });
}

export function disableAiPolicy(id: string): Promise<void> {
  return apiSend(policyPath(id), { method: 'DELETE' });
}

export function listAiOverrides(policyId: string): Promise<AiOverride[]> {
  return apiCall(`${policyPath(policyId)}/overrides`, { schema: overridesSchema }).then(
    (page) => page.items,
  );
}

export function createAiOverride(policyId: string, body: AiOverrideInput): Promise<AiOverride> {
  return apiCall(`${policyPath(policyId)}/overrides`, {
    method: 'POST',
    body,
    schema: overrideSchema,
  });
}

export function revokeAiOverride(id: string): Promise<AiOverride> {
  return apiCall(`/api/admin/ai-usage/overrides/${encodeURIComponent(id)}`, {
    method: 'DELETE',
    schema: overrideSchema,
  });
}

export function getMyAiUsage(): Promise<AiUsagePage> {
  return apiCall('/api/ai-usage/me', { schema: pageSchema });
}

export function getTeamAiUsage(teamId: string): Promise<TeamAiUsage> {
  return apiCall(`/api/teams/${encodeURIComponent(teamId)}/ai-usage`, { schema: teamSchema });
}

export type PreviewTarget = { system: true } | { system?: false; userId: string; teamId?: string };

export function previewAiUsage(target: PreviewTarget): Promise<AiUsagePreview> {
  const params = new URLSearchParams();
  if (target.system) {
    params.set('system', 'true');
  } else {
    params.set('user_id', target.userId);
    if (target.teamId) params.set('team_id', target.teamId);
  }
  return apiCall(`/api/admin/ai-usage/preview?${params.toString()}`, { schema: previewSchema });
}

/** The suggested starting set. Reading it never changes a policy. */
export function getAiPolicyDefaults(): Promise<AiPolicyDefaults> {
  return apiCall('/api/admin/ai-usage/defaults', { schema: defaultsSchema });
}

/** Deliberately create every missing policy in the suggested set. */
export function applyAiPolicyDefaults(): Promise<AiPolicy[]> {
  return apiCall('/api/admin/ai-usage/defaults', {
    method: 'POST',
    schema: appliedSchema,
  }).then((body) => body.created);
}
