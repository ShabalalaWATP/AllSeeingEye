import type { StatusTone } from '@/components/admin/StatusPill';
import type { Source } from '@/lib/api/eventSchemas';

export type ScheduledSourceStatus =
  'healthy' | 'failing' | 'blockedUpstream' | 'idle' | 'switchedOff' | 'blockedByOperator';

/** The admin API exposes a test connector only for scheduled sources. */
export const isOnDemandSource = (source: Source): boolean => source.test_available === false;

/** Operator choices take precedence over retained health from an earlier poll. */
export function scheduledSourceStatus(source: Source): ScheduledSourceStatus {
  if (source.environment_disabled === true) return 'blockedByOperator';
  if (source.enabled === false) return 'switchedOff';
  if (source.health.status === 'disabled') return 'failing';
  if (source.health.status === 'degraded')
    return source.health.blocked_reason ? 'blockedUpstream' : 'failing';
  return source.health.status;
}

const STATUS_PRESENTATION: Record<ScheduledSourceStatus, { label: string; tone: StatusTone }> = {
  healthy: { label: 'healthy', tone: 'good' },
  failing: { label: 'degraded', tone: 'critical' },
  blockedUpstream: { label: 'Blocked upstream', tone: 'warning' },
  idle: { label: 'idle', tone: 'info' },
  switchedOff: { label: 'Switched off', tone: 'neutral' },
  blockedByOperator: { label: 'Blocked by operator', tone: 'warning' },
};

export function sourceStatusPresentation(source: Source): { label: string; tone: StatusTone } {
  const state = scheduledSourceStatus(source);
  if (state === 'blockedByOperator' || state === 'switchedOff') return STATUS_PRESENTATION[state];
  if (isOnDemandSource(source)) return { label: 'On-demand', tone: 'info' };
  if (state === 'healthy' && source.health.warning)
    return { label: 'Live with warning', tone: 'warning' };
  if (source.health.status === 'disabled')
    return { label: 'Paused after failures', tone: 'critical' };
  return STATUS_PRESENTATION[state];
}
