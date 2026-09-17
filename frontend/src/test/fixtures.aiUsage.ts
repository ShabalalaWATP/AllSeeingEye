import type {
  AiOverride,
  AiPolicy,
  AiPolicyDefaults,
  AiTokenPrices,
  AiUsagePage,
  AiUsagePreview,
  AiUsageSummary,
  AiUsageTotals,
  TeamAiUsage,
} from '@/lib/api/aiUsage';

export const policyId = '11111111-1111-4111-8111-111111111111';
export const teamId = '22222222-2222-4222-8222-222222222222';

export function aiPolicy(overrides: Partial<AiPolicy> = {}): AiPolicy {
  return {
    id: policyId,
    scope: 'global',
    target_id: null,
    period: 'month',
    request_limit: 10,
    token_limit: 1000,
    enabled: true,
    revision: 1,
    created_at: '2026-09-01T00:00:00Z',
    updated_at: '2026-09-01T00:00:00Z',
    ...overrides,
  };
}

/** GPT-5.6 Luna, the operator's current model, at the shipped default prices. */
export function aiPrices(overrides: Partial<AiTokenPrices> = {}): AiTokenPrices {
  return {
    input_per_million: 0.2,
    output_per_million: 1.2,
    currency: 'USD',
    configured: true,
    ...overrides,
  };
}

export function aiTotals(overrides: Partial<AiUsageTotals> = {}): AiUsageTotals {
  return {
    period_start: '2026-09-01T00:00:00Z',
    period_end: '2026-10-01T00:00:00Z',
    used_requests: 0,
    used_tokens: 0,
    unknown_requests: 0,
    used_input_tokens: 0,
    used_output_tokens: 0,
    estimated_cost: '0.0000',
    ...overrides,
  };
}

export function aiOverride(overrides: Partial<AiOverride> = {}): AiOverride {
  return {
    id: '33333333-3333-4333-8333-333333333333',
    policy_id: policyId,
    requests: { state: 'blocked', value: null },
    tokens: { state: 'inherit', value: null },
    effective_from: '2026-09-01T00:00:00Z',
    expires_at: '2026-09-08T00:00:00Z',
    created_by: '44444444-4444-4444-8444-444444444444',
    created_at: '2026-09-01T00:00:00Z',
    revoked_at: null,
    ...overrides,
  };
}

export function aiSummary(overrides: Partial<AiUsageSummary> = {}): AiUsageSummary {
  const policy = overrides.policy ?? aiPolicy();
  return {
    policy,
    period_start: '2026-09-01T00:00:00Z',
    period_end: '2026-10-01T00:00:00Z',
    request_limit: policy.request_limit,
    token_limit: policy.token_limit,
    override: null,
    used_requests: 1,
    reserved_requests: 0,
    remaining_requests: 9,
    used_tokens: 100,
    reserved_tokens: 0,
    remaining_tokens: 900,
    ...overrides,
  };
}

export function aiPage(overrides: Partial<AiUsagePage> = {}): AiUsagePage {
  return { items: [], observed: aiTotals(), prices: aiPrices(), ...overrides };
}

export function aiPreview(overrides: Partial<AiUsagePreview> = {}): AiUsagePreview {
  return {
    items: [],
    observed: aiTotals(),
    unknown_calls: 0,
    prices: aiPrices(),
    model: null,
    ...overrides,
  };
}

export function teamUsage(overrides: Partial<TeamAiUsage> = {}): TeamAiUsage {
  return {
    team_id: teamId,
    view: 'member',
    items: [],
    own: aiTotals({ used_requests: 2, used_tokens: 40 }),
    team: null,
    members: null,
    prices: aiPrices(),
    ...overrides,
  };
}

export function aiDefaults(overrides: Partial<AiPolicyDefaults> = {}): AiPolicyDefaults {
  return {
    items: [
      {
        scope: 'global',
        target_id: null,
        target_name: 'Everyone',
        period: 'day',
        token_limit: 300_000,
        reason: 'A daily ceiling for the whole site, so one bad day cannot run away.',
        already_configured: false,
      },
      {
        scope: 'system',
        target_id: null,
        target_name: 'System work',
        period: 'day',
        token_limit: 100_000,
        reason: 'A separate daily budget for unattended background work.',
        already_configured: true,
      },
    ],
    observed: aiTotals({
      used_requests: 912,
      used_tokens: 969_000,
      used_input_tokens: 100_000,
      used_output_tokens: 869_000,
      estimated_cost: '1.0628',
    }),
    observed_daily_tokens: 194_000,
    enforcing: false,
    prices: aiPrices(),
    ...overrides,
  };
}
