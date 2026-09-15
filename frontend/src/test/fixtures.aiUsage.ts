import type {
  AiOverride,
  AiPolicy,
  AiUsagePage,
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

export function aiTotals(overrides: Partial<AiUsageTotals> = {}): AiUsageTotals {
  return {
    period_start: '2026-09-01T00:00:00Z',
    period_end: '2026-10-01T00:00:00Z',
    used_requests: 0,
    used_tokens: 0,
    unknown_requests: 0,
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
  return { items: [], observed: aiTotals(), ...overrides };
}

export function teamUsage(overrides: Partial<TeamAiUsage> = {}): TeamAiUsage {
  return {
    team_id: teamId,
    view: 'member',
    items: [],
    own: aiTotals({ used_requests: 2, used_tokens: 40 }),
    team: null,
    members: null,
    ...overrides,
  };
}
