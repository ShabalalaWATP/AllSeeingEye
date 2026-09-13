import type { CatalogueSource, ConnectionState, PlatformConnection } from '@/lib/api/sourceContext';

export type ConnectionTone = 'good' | 'amber' | 'critical' | 'cyan' | 'muted';
export type ConnectionGroup = 'collecting' | 'attention' | 'key_missing' | 'on_demand' | 'off';

export interface ConnectionMeta {
  label: string;
  tone: ConnectionTone;
  group: ConnectionGroup;
}

/** One vocabulary for sources and platform services; the group drives filters and totals. */
export const CONNECTION_META: Record<ConnectionState, ConnectionMeta> = {
  connected: { label: 'Connected', tone: 'good', group: 'collecting' },
  idle: { label: 'Waiting for first collection', tone: 'cyan', group: 'collecting' },
  key_unverified: { label: 'Key set, unverified', tone: 'amber', group: 'attention' },
  degraded: { label: 'Degraded', tone: 'amber', group: 'attention' },
  failing: { label: 'Failing', tone: 'critical', group: 'attention' },
  key_missing: { label: 'API key missing', tone: 'critical', group: 'key_missing' },
  not_configured: { label: 'Not configured', tone: 'amber', group: 'key_missing' },
  on_demand: { label: 'Available on demand', tone: 'cyan', group: 'on_demand' },
  disabled_by_admin: { label: 'Switched off', tone: 'muted', group: 'off' },
  disabled_by_environment: { label: 'Excluded by configuration', tone: 'muted', group: 'off' },
};

export const GROUP_LABELS: Record<ConnectionGroup, string> = {
  collecting: 'Collecting',
  attention: 'Needs attention',
  key_missing: 'Key or setup missing',
  on_demand: 'On demand',
  off: 'Switched off',
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

export interface ConnectionTotals {
  total: number;
  collecting: number;
  attention: number;
  key_missing: number;
  on_demand: number;
  off: number;
}

export function summariseConnections(
  sources: readonly CatalogueSource[],
  platform: readonly PlatformConnection[] = [],
): ConnectionTotals {
  const totals: ConnectionTotals = {
    total: sources.length + platform.length,
    collecting: 0,
    attention: 0,
    key_missing: 0,
    on_demand: 0,
    off: 0,
  };
  for (const state of [
    ...sources.map((source) => source.connection.state),
    ...platform.map((item) => item.state),
  ])
    totals[connectionGroup(state)] += 1;
  return totals;
}

/** Sources whose credential or setup is missing, worst first, for the attention list. */
export function attentionSources(sources: readonly CatalogueSource[]): CatalogueSource[] {
  const rank: Record<ConnectionGroup, number> = {
    attention: 0,
    key_missing: 1,
    off: 2,
    collecting: 3,
    on_demand: 4,
  };
  return sources
    .filter((source) => {
      const group = connectionGroup(source.connection.state);
      return (
        group === 'attention' ||
        (group === 'key_missing' && !source.connection.requirement?.optional)
      );
    })
    .sort(
      (a, b) =>
        rank[connectionGroup(a.connection.state)] - rank[connectionGroup(b.connection.state)] ||
        a.name.localeCompare(b.name, 'en-GB'),
    );
}
