import { StatusPill } from '@/components/admin/StatusPill';
import { Td } from '@/components/ui/Table';
import type { Source, SourceHealth } from '@/lib/api/eventSchemas';
import { formatAgo, formatInterval } from '@/lib/format';
import { SourceActions } from './SourceActions';
import { isOnDemandSource, sourceStatusPresentation } from './sourceStatus';

export interface SourceRowProps {
  source: Source;
  now: number;
  onReset: (health: SourceHealth) => void;
  onActivation: (id: string, enabled: boolean) => void;
}

/** One feed: what it is, how it is graded, how its last poll went, and a reset button. */
export function SourceRow({ source, now, onReset, onActivation }: SourceRowProps) {
  const health = source.health;
  const onDemand = isOnDemandSource(source);
  const stopped = source.environment_disabled === true || source.enabled === false;
  const status = sourceStatusPresentation(source);
  const lastPoll =
    health.last_success === null
      ? 'never'
      : `${health.items_last_poll} items, ${formatAgo(health.last_success, now)}`;
  return (
    <tr>
      <Td className="min-w-60 py-3">
        <div className="font-medium text-text">{source.name}</div>
        <div className="text-xs text-muted">{source.organisation}</div>
        <div className={`mt-1 text-xs ${source.enabled === false ? 'text-amber' : 'text-muted'}`}>
          Collection {source.enabled === false ? 'disabled' : 'enabled'}
        </div>
        {source.licence_note && (
          <p className="mt-1 max-w-sm text-xs text-muted">{source.licence_note}</p>
        )}
        {source.flags.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {source.flags.map((flag) => (
              <span
                key={flag}
                className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] text-muted"
              >
                {flag.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        )}
      </Td>
      <Td className="capitalize">{source.category}</Td>
      <Td className="font-mono">{source.reliability}</Td>
      <Td className="font-mono whitespace-nowrap">
        {onDemand ? 'Not scheduled' : formatInterval(source.poll_interval_seconds)}
      </Td>
      <Td>
        <StatusPill tone={status.tone}>{status.label}</StatusPill>
        {!onDemand && !stopped && health.warning && (
          <p className="mt-1 max-w-xs text-xs text-amber">{health.warning}</p>
        )}
        {!onDemand && !stopped && health.consecutive_failures > 0 && (
          <span className="mt-1 block text-[11px] text-muted">
            {health.consecutive_failures} failed in a row
          </span>
        )}
      </Td>
      <Td className="whitespace-nowrap">
        {onDemand ? 'Not applicable' : lastPoll}
        {!onDemand && health.last_latency_ms !== null && (
          <span className="ml-1 font-mono text-xs text-muted">
            {Math.round(health.last_latency_ms)} ms
          </span>
        )}
      </Td>
      <Td className="max-w-xs">
        {!onDemand && health.last_error !== null && (
          <span className="block truncate text-xs text-critical" title={health.last_error}>
            {health.last_error}
          </span>
        )}
      </Td>
      <Td className="min-w-64 py-3">
        <SourceActions source={source} onReset={onReset} onActivation={onActivation} />
      </Td>
    </tr>
  );
}
