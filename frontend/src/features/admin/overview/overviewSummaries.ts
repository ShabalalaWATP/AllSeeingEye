/** Pure summaries for the administration overview. Each works on bounded API responses. */
import type { AiUsagePreview, AiUsageSummary } from '@/lib/api/aiUsage';
import type { Source } from '@/lib/api/eventSchemas';
import type { LlmConnection, LlmProfilesResponse } from '@/lib/api/llm';
import type { User } from '@/lib/api/schemas';
import type { Team } from '@/lib/api/teams';

import { legacyConnections } from '../llmPresentation';
import { isOnDemandSource, scheduledSourceStatus } from '../sourceStatus';

export interface UserSummary {
  total: number;
  active: number;
  inactive: number;
  admins: number;
  neverSignedIn: number;
}

export function summariseUsers(users: readonly User[]): UserSummary {
  const active = users.filter((user) => user.is_active);
  return {
    total: users.length,
    active: active.length,
    inactive: users.length - active.length,
    admins: active.filter((user) => user.role === 'admin').length,
    neverSignedIn: users.filter((user) => user.last_login_at === null).length,
  };
}

export function summariseTeams(teams: readonly Team[]) {
  const active = teams.filter((team) => team.is_active).length;
  return { total: teams.length, active, archived: teams.length - active };
}

export interface SourceSummary {
  total: number;
  scheduled: number;
  onDemand: number;
  healthy: number;
  failing: number;
  idle: number;
  switchedOff: number;
  blockedByOperator: number;
  blockedUpstream: number;
  attention: Source[];
}

/** Failing feeds first (most consecutive failures), then upstream refusals, then operator blocks. */
export function summariseSources(sources: readonly Source[]): SourceSummary {
  const scheduled = sources.filter((source) => !isOnDemandSource(source));
  const upstream = scheduled.filter((item) => scheduledSourceStatus(item) === 'blockedUpstream');
  const failing = scheduled
    .filter((item) => scheduledSourceStatus(item) === 'failing')
    .sort((a, b) => b.health.consecutive_failures - a.health.consecutive_failures);
  const blocked = scheduled.filter((item) => scheduledSourceStatus(item) === 'blockedByOperator');
  const switchedOff = scheduled.filter((item) => scheduledSourceStatus(item) === 'switchedOff');
  return {
    total: sources.length,
    scheduled: scheduled.length,
    onDemand: sources.length - scheduled.length,
    healthy: scheduled.filter((item) => scheduledSourceStatus(item) === 'healthy').length,
    failing: failing.length,
    idle: scheduled.filter((item) => scheduledSourceStatus(item) === 'idle').length,
    switchedOff: switchedOff.length,
    blockedByOperator: blocked.length,
    blockedUpstream: upstream.length,
    attention: [...failing, ...upstream, ...blocked],
  };
}

export interface ConnectionStatus {
  encryption: boolean;
  global: { name: string; model: string; tested: boolean } | null;
  /** Role-based profiles still in use because no connection has been applied yet. */
  legacy: number;
  teamOverrides: number;
  personalOverrides: number;
  drafts: number;
  untestedDrafts: number;
}

export function summariseConnections(
  profiles: LlmProfilesResponse,
  connections: readonly LlmConnection[],
): ConnectionStatus {
  const binding = connections.find((item) => item.team_id === null && !item.user_id);
  const profile =
    binding === undefined
      ? undefined
      : profiles.items.find((item) => item.id === binding.profile_id);
  const drafts = profiles.items.filter((item) => !item.is_bound);
  return {
    encryption: profiles.encryption_available,
    global:
      profile === undefined
        ? null
        : {
            name: profile.name,
            model: profile.model,
            tested: profile.is_tested && profile.tested_revision === profile.revision,
          },
    legacy: connections.length === 0 ? legacyConnections(profiles.items).length : 0,
    teamOverrides: connections.filter((item) => item.team_id !== null).length,
    personalOverrides: connections.filter((item) => Boolean(item.user_id)).length,
    drafts: drafts.length,
    untestedDrafts: drafts.filter((item) => !item.is_tested).length,
  };
}

export interface UsageStatus {
  site: AiUsageSummary | null;
  system: AiUsageSummary | null;
  systemRequests: number;
  systemTokens: number;
  unknownCalls: number;
  periodEnd: string;
}

/** The site-wide policy covers every call; the system policy covers shared unattended work. */
export function summariseUsage(preview: AiUsagePreview): UsageStatus {
  return {
    site: preview.items.find((item) => item.policy.scope === 'global') ?? null,
    system: preview.items.find((item) => item.policy.scope === 'system') ?? null,
    systemRequests: preview.observed.used_requests,
    systemTokens: preview.observed.used_tokens,
    unknownCalls: preview.unknown_calls,
    periodEnd: preview.observed.period_end,
  };
}

/** Human action names: `account_request_approved` becomes "Account request approved". */
const ACRONYMS: Record<string, string> = {
  ai: 'AI',
  api: 'API',
  firms: 'FIRMS',
  ip: 'IP',
  llm: 'LLM',
  mfa: 'MFA',
  totp: 'TOTP',
};

export function describeAction(action: string): string {
  const words = action
    .split(/[_.\s]+/)
    .filter((word) => word !== '')
    .map((word) => ACRONYMS[word.toLowerCase()] ?? word.toLowerCase());
  if (words.length === 0) return action;
  const [first = '', ...rest] = words;
  return [first.charAt(0).toUpperCase() + first.slice(1), ...rest].join(' ');
}

export function compactNumber(value: number): string {
  // Compact dashboard notation uses K/M/B/T across browser and ICU versions.
  return new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(
    value,
  );
}
