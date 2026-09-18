import type { AiPolicy } from '@/lib/api/aiUsage';

export type AllowancePreset = 'light' | 'standard' | 'intensive' | 'power' | 'blocked' | 'inherit';
export type DisplayAllowancePreset = AllowancePreset | 'custom';

/** Presets change only this audience's daily policy. Other periods stay in force. */
export const ALLOWANCE_PRESETS = [
  { value: 'light', label: 'Light', request_limit: 50, token_limit: 100_000 },
  { value: 'standard', label: 'Standard', request_limit: 250, token_limit: 500_000 },
  { value: 'intensive', label: 'Intensive', request_limit: 1_000, token_limit: 2_000_000 },
  { value: 'power', label: 'Power', request_limit: 2_500, token_limit: 5_000_000 },
  { value: 'blocked', label: 'Blocked', request_limit: 0, token_limit: 0 },
] as const;

export function allowancePresetLimits(preset: Exclude<AllowancePreset, 'inherit'>): {
  request_limit: number;
  token_limit: number;
} {
  const selected = ALLOWANCE_PRESETS.find((item) => item.value === preset);
  if (!selected) throw new Error('Unknown allowance preset');
  return { request_limit: selected.request_limit, token_limit: selected.token_limit };
}

/** Custom policies are display-only, so changing a model never rewrites their limits. */
export function currentAllowancePreset(policies: readonly AiPolicy[]): DisplayAllowancePreset {
  const daily = policies.filter((policy) => policy.enabled && policy.period === 'day');
  if (daily.length === 0) return 'inherit';
  if (daily.length !== 1) return 'custom';
  const policy = daily[0];
  return (
    ALLOWANCE_PRESETS.find(
      (item) =>
        item.request_limit === policy?.request_limit && item.token_limit === policy.token_limit,
    )?.value ?? 'custom'
  );
}

export function describeAllowanceLimits(policy: Pick<AiPolicy, 'request_limit' | 'token_limit'>) {
  const requests =
    policy.request_limit === null
      ? 'no separate request cap'
      : `${policy.request_limit.toLocaleString('en-GB')} requests`;
  const tokens =
    policy.token_limit === null
      ? 'no separate token cap'
      : `${policy.token_limit.toLocaleString('en-GB')} tokens`;
  return `${requests} · ${tokens}`;
}

export function describePreset(preset: DisplayAllowancePreset, policies: readonly AiPolicy[]) {
  if (preset === 'inherit') return 'Other applicable limits still apply.';
  if (preset === 'custom') {
    return policies
      .filter((policy) => policy.enabled && policy.period === 'day')
      .map(describeAllowanceLimits)
      .join('; ');
  }
  if (preset === 'blocked') return 'Daily requests blocked.';
  return `${describeAllowanceLimits(allowancePresetLimits(preset))} per day`;
}
