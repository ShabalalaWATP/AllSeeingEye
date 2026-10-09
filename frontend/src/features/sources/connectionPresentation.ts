import type { ConnectionState, SourceRequirement } from '@/lib/api/sourceContext';

export type ConnectionTone = 'good' | 'amber' | 'critical' | 'cyan' | 'muted';
export type ConnectionGroup =
  'live' | 'unconfirmed' | 'retrying' | 'setup' | 'blocked' | 'licence' | 'on_demand' | 'off';

export interface ConnectionMeta {
  label: string;
  tone: ConnectionTone;
  group: ConnectionGroup;
}

/**
 * One vocabulary for sources, data assets and platform services; the group drives totals.
 * A feed with no successful collection yet is unconfirmed, never counted as live.
 */
export const CONNECTION_META: Record<ConnectionState, ConnectionMeta> = {
  connected: { label: 'Connected', tone: 'good', group: 'live' },
  available: { label: 'Available', tone: 'good', group: 'live' },
  idle: { label: 'Waiting for first collection', tone: 'cyan', group: 'unconfirmed' },
  key_unverified: { label: 'Key set, awaiting collection', tone: 'cyan', group: 'unconfirmed' },
  degraded: { label: 'Retrying', tone: 'amber', group: 'retrying' },
  failing: { label: 'Failing', tone: 'critical', group: 'retrying' },
  key_missing: { label: 'API key missing', tone: 'critical', group: 'setup' },
  not_configured: { label: 'Setup missing', tone: 'amber', group: 'setup' },
  blocked_upstream: { label: 'Blocked upstream', tone: 'critical', group: 'blocked' },
  on_demand: { label: 'On demand', tone: 'cyan', group: 'on_demand' },
  disabled_by_admin: { label: 'Switched off by an administrator', tone: 'muted', group: 'off' },
  disabled_by_environment: { label: 'Off on this server', tone: 'muted', group: 'off' },
  disabled_by_licence: {
    label: 'Unavailable due to licence terms',
    tone: 'amber',
    group: 'licence',
  },
};

export const GROUPS: readonly ConnectionGroup[] = [
  'live',
  'unconfirmed',
  'on_demand',
  'setup',
  'blocked',
  'licence',
  'retrying',
  'off',
];

export const GROUP_LABELS: Record<ConnectionGroup, string> = {
  live: 'Live or available',
  unconfirmed: 'Not yet confirmed',
  on_demand: 'On demand',
  setup: 'Needs key or setup',
  blocked: 'Blocked upstream',
  licence: 'Licence unavailable',
  retrying: 'Retrying or failing',
  off: 'Off by operator choice',
};

export const GROUP_TONE: Record<ConnectionGroup, string> = {
  live: 'text-good',
  unconfirmed: 'text-cyan',
  on_demand: 'text-cyan',
  setup: 'text-critical',
  blocked: 'text-critical',
  licence: 'text-amber',
  retrying: 'text-amber',
  off: 'text-muted',
};

export const TONE_CLASSES: Record<ConnectionTone, string> = {
  good: 'border-good/40 bg-good/10 text-good',
  amber: 'border-amber/40 bg-amber/10 text-amber',
  critical: 'border-critical/40 bg-critical/10 text-critical',
  cyan: 'border-cyan/40 bg-cyan/10 text-cyan',
  muted: 'border-line bg-surface-2 text-muted',
};

export function connectionGroup(state: ConnectionState): ConnectionGroup {
  return CONNECTION_META[state].group;
}

/** Only states an operator can act on: a missing required setting, a paused feed or a refusal. */
export function isActionable(state: ConnectionState, requirement: SourceRequirement | null) {
  const group = connectionGroup(state);
  if (group === 'setup') return !requirement?.optional;
  return state === 'failing' || group === 'blocked' || group === 'licence';
}

const ACTION_RANK: Partial<Record<ConnectionState, number>> = {
  disabled_by_licence: 0,
  blocked_upstream: 0,
  failing: 1,
  key_missing: 2,
  not_configured: 3,
};

export function actionRank(state: ConnectionState) {
  return ACTION_RANK[state] ?? 4;
}
