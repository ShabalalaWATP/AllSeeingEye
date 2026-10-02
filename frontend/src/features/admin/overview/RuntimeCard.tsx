import { StatusPill } from '@/components/admin/StatusPill';
import { fetchRuntimeHealth } from '@/lib/api/runtime';
import { formatUtc } from '@/lib/format';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

import { OverviewCard, StatList } from './OverviewCard';

const megabytes = (value: number) => `${(value / (1024 * 1024)).toFixed(1)} MiB`;

export function RuntimeCard() {
  const resource = useScopedResource(fetchRuntimeHealth);
  return (
    <OverviewCard
      title="Runtime health"
      to="/admin"
      icon="sources"
      resource={resource}
      className="md:col-span-2 xl:col-span-3"
    >
      {(runtime) => (
        <>
          <StatusPill tone={runtime.ready ? 'good' : 'critical'}>
            {runtime.ready ? 'Workers are current' : 'Readiness degraded'}
          </StatusPill>
          <StatList
            items={[
              { label: 'Stream drops since restart', value: runtime.stream_drops },
              { label: 'Stream subscribers', value: runtime.bus_subscribers },
              { label: 'Queued reports', value: runtime.job_queue_depth },
              { label: 'Loop lag (p99)', value: `${runtime.loop_lag_p99_ms.toFixed(1)} ms` },
              {
                label: 'Live store',
                value: `${megabytes(runtime.store_bytes)} / ${megabytes(runtime.store_budget_bytes)}`,
              },
              {
                label: 'Process memory',
                value: runtime.rss_bytes === null ? 'Unavailable' : megabytes(runtime.rss_bytes),
              },
              { label: 'Read requests refused', value: runtime.read_rejections },
              { label: 'Queued stream messages', value: runtime.bus_queue_depth },
              { label: 'Cached stream characters', value: runtime.stream_encoder_cached_chars },
            ]}
          />
          <details className="mt-4">
            <summary className="cursor-pointer text-sm font-medium">
              Worker freshness ({runtime.workers.length})
            </summary>
            {runtime.workers.length === 0 ? (
              <p className="mt-2 text-sm text-muted">No workers have started in this process.</p>
            ) : (
              <ul
                aria-label="Worker freshness"
                className="mt-2 max-h-64 space-y-2 overflow-auto text-sm"
              >
                {runtime.workers.map((worker) => (
                  <li
                    key={worker.name}
                    className="flex flex-wrap items-baseline justify-between gap-2 border-b border-line/60 py-2"
                  >
                    <span>{worker.name}</span>
                    <span className="text-muted">
                      {worker.last_cycle === null
                        ? 'Awaiting first cycle'
                        : `Last cycle ${formatUtc(worker.last_cycle)}`}
                    </span>
                    <StatusPill
                      tone={
                        worker.overdue ? 'critical' : worker.last_error_code ? 'warning' : 'good'
                      }
                    >
                      {worker.overdue
                        ? 'Overdue'
                        : worker.last_error_code
                          ? 'Cycle failed'
                          : 'Current'}
                    </StatusPill>
                  </li>
                ))}
              </ul>
            )}
          </details>
          <p className="mt-3 text-xs text-muted">
            Workers become overdue after three expected intervals. Source outages are tracked
            separately in Sources.
          </p>
        </>
      )}
    </OverviewCard>
  );
}
