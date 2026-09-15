import type { AiLimitState, AiPolicy } from '@/lib/api/aiUsage';
import type { User } from '@/lib/api/schemas';
import type { Team } from '@/lib/api/teams';

/** Blank means unlimited; anything else must be a whole number, where zero blocks. */
export function parseLimit(value: string): number | null {
  if (value.trim() === '') return null;
  const number = Number(value);
  return Number.isSafeInteger(number) && number >= 0 ? number : Number.NaN;
}

export function policyLabel(
  policy: AiPolicy,
  users: readonly User[],
  teams: readonly Team[],
): string {
  if (policy.scope === 'global') return 'Everyone';
  if (policy.scope === 'system') return 'System work';
  const target = policy.target_id;
  if (target === null) return policy.scope;
  if (policy.scope === 'user') {
    const user = users.find((item) => item.id === target);
    return user === undefined ? `User · ${target}` : `User · ${user.display_name} (${user.email})`;
  }
  const team = teams.find((item) => item.id === target);
  return team === undefined ? `Team · ${target}` : `Team · ${team.name}`;
}

export const LIMIT_STATE_OPTIONS: readonly { value: AiLimitState; label: string }[] = [
  { value: 'inherit', label: 'Keep policy limit' },
  { value: 'limit', label: 'Set a limit' },
  { value: 'unlimited', label: 'Unlimited' },
  { value: 'blocked', label: 'Blocked' },
];

export function describeOverrideLimit(state: AiLimitState, value: number | null): string {
  if (state === 'limit') return value === 0 ? 'Blocked (0)' : `${value ?? 0}`;
  return LIMIT_STATE_OPTIONS.find((option) => option.value === state)?.label ?? state;
}
