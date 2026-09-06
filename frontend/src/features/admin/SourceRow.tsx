import { Td } from '@/components/ui/Table';
import type { Source, SourceHealth } from '@/lib/api/eventSchemas';
import { formatAgo, formatInterval } from '@/lib/format';
import { SourceActions } from './SourceActions';

const STATUS_CLASSES: Record<SourceHealth['status'], string> = {
  healthy: 'bg-emerald-400/15 text-emerald-300',
  degraded: 'bg-amber-400/15 text-amber-300',
  idle: 'bg-zinc-500/15 text-zinc-300',
  disabled: 'bg-zinc-500/15 text-muted',
};

export interface SourceRowProps {
  source: Source;
  now: number;
  onReset: (health: SourceHealth) => void;
  onActivation: (id: string, enabled: boolean) => void;
}

/** One feed: what it is, how it is graded, how its last poll went, and a reset button. */
export function SourceRow({ source, now, onReset, onActivation }: SourceRowProps) {
  const health = source.health;
  const lastPoll =
    health.last_success === null
      ? 'never'
      : `${health.items_last_poll} items, ${formatAgo(health.last_success, now)}`;
  return (
    <tr>
      <Td>
        <div className="font-medium text-text">{source.name}</div>
        <div className="text-xs text-muted">{source.organisation}</div>
        <div className="mt-1 text-xs text-muted">
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
        {formatInterval(source.poll_interval_seconds)}
      </Td>
      <Td>
        <span
          className={`rounded px-1.5 py-0.5 font-mono text-[11px] uppercase ${STATUS_CLASSES[health.status]}`}
        >
          {health.status}
        </span>
      </Td>
      <Td className="whitespace-nowrap">
        {lastPoll}
        {health.last_latency_ms !== null && (
          <span className="ml-1 font-mono text-xs text-muted">
            {Math.round(health.last_latency_ms)} ms
          </span>
        )}
      </Td>
      <Td className="max-w-xs">
        {health.last_error !== null && (
          <span className="block truncate text-xs text-critical" title={health.last_error}>
            {health.last_error}
          </span>
        )}
      </Td>
      <Td>
        <SourceActions source={source} onReset={onReset} onActivation={onActivation} />
      </Td>
    </tr>
  );
}
