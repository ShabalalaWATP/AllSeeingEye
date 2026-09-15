import { StatusPill, type StatusTone } from '@/components/admin/StatusPill';
import { UsageBar } from '@/components/aiUsage/AllowanceCards';
import { previewAiUsage } from '@/lib/api/aiUsage';
import { fetchSources } from '@/lib/api/events';
import { fetchLlmConnections, fetchLlmProfiles } from '@/lib/api/llm';
import { formatUtc } from '@/lib/format';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

import { Figure, OverviewCard, StatList } from './OverviewCard';
import {
  compactNumber,
  summariseConnections,
  summariseSources,
  summariseUsage,
} from './overviewSummaries';

const loadConnectionStatus = async () => {
  const [profiles, connections] = await Promise.all([fetchLlmProfiles(), fetchLlmConnections()]);
  return summariseConnections(profiles, connections.items);
};
const loadSystemUsage = async () => summariseUsage(await previewAiUsage({ system: true }));

const SEGMENTS: readonly {
  key: 'healthy' | 'failing' | 'idle' | 'switchedOff' | 'blockedByOperator';
  label: string;
  bar: string;
  tone: StatusTone;
}[] = [
  { key: 'healthy', label: 'Live', bar: 'bg-good', tone: 'good' },
  { key: 'failing', label: 'Failing', bar: 'bg-critical', tone: 'critical' },
  { key: 'idle', label: 'Waiting', bar: 'bg-cyan', tone: 'info' },
  { key: 'switchedOff', label: 'Switched off', bar: 'bg-muted', tone: 'neutral' },
  { key: 'blockedByOperator', label: 'Blocked by operator', bar: 'bg-amber', tone: 'warning' },
];

export function SourcesCard({ className = '' }: { className?: string }) {
  const resource = useScopedResource(fetchSources);
  return (
    <OverviewCard
      title="Sources"
      to="/admin/sources"
      icon="sources"
      resource={resource}
      className={className}
    >
      {(sources) => {
        const summary = summariseSources(sources);
        if (summary.total === 0)
          return <p className="text-sm text-muted">No collection sources are registered.</p>;
        return (
          <>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Figure value={`${summary.healthy}/${summary.total}`} caption="sources live" />
              {summary.failing > 0 ? (
                <StatusPill tone="critical">{summary.failing} failing</StatusPill>
              ) : (
                <StatusPill tone="good">No failing feeds</StatusPill>
              )}
            </div>
            <div
              aria-hidden="true"
              className="mt-4 flex h-2 overflow-hidden rounded-full bg-surface-2"
            >
              {SEGMENTS.map((segment) =>
                summary[segment.key] === 0 ? null : (
                  <span
                    key={segment.key}
                    className={`${segment.bar} h-full border-r border-surface last:border-r-0`}
                    style={{ width: `${(summary[segment.key] / summary.total) * 100}%` }}
                  />
                ),
              )}
            </div>
            <ul aria-label="Source status counts" className="mt-3 flex flex-wrap gap-1.5">
              {SEGMENTS.map((segment) => (
                <li key={segment.key}>
                  <StatusPill tone={segment.tone}>
                    {segment.label}: {summary[segment.key]}
                  </StatusPill>
                </li>
              ))}
            </ul>
            {summary.attention.length === 0 ? null : (
              <div className="mt-4 border-t border-line/60 pt-3">
                <h3 className="text-xs font-semibold tracking-wide text-muted uppercase">
                  Needs attention
                </h3>
                <ul className="mt-2 space-y-2">
                  {summary.attention.slice(0, 3).map((source) => (
                    <li key={source.id} className="flex min-w-0 flex-wrap items-center gap-2">
                      {source.environment_disabled === true ? (
                        <StatusPill tone="warning">Blocked</StatusPill>
                      ) : (
                        <StatusPill tone="critical">
                          {source.health.consecutive_failures} failed polls
                        </StatusPill>
                      )}
                      <span className="text-sm font-medium">{source.name}</span>
                      {source.health.last_error === null ? null : (
                        <span
                          className="block w-full truncate font-mono text-[11px] text-muted"
                          title={source.health.last_error}
                        >
                          {source.health.last_error}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        );
      }}
    </OverviewCard>
  );
}

export function ConnectionsCard() {
  const resource = useScopedResource(loadConnectionStatus);
  return (
    <OverviewCard title="AI connections" to="/admin/llm" icon="ai" resource={resource}>
      {(status) => (
        <>
          <div className="flex flex-wrap items-center gap-2">
            {status.global === null && status.legacy > 0 ? (
              <StatusPill tone="warning">Role-based connections in use</StatusPill>
            ) : status.global === null ? (
              <StatusPill tone="critical">No global connection</StatusPill>
            ) : status.global.tested ? (
              <StatusPill tone="good">Global connection tested</StatusPill>
            ) : (
              <StatusPill tone="warning">Global connection needs a test</StatusPill>
            )}
            {status.encryption ? null : (
              <StatusPill tone="warning">Key storage unavailable</StatusPill>
            )}
          </div>
          {status.global === null && status.legacy > 0 ? (
            <p className="mt-3 text-sm text-muted">
              Existing role selection remains in use until a tested global connection is applied.
            </p>
          ) : status.global === null ? (
            <p className="mt-3 text-sm text-muted">
              Research and reports cannot reach a model until a tested connection is applied.
            </p>
          ) : (
            <div className="mt-3 min-w-0">
              <p className="truncate text-sm font-medium">{status.global.name}</p>
              <p className="truncate font-mono text-xs text-muted">{status.global.model}</p>
            </div>
          )}
          <StatList
            items={[
              { label: 'Team overrides', value: status.teamOverrides },
              { label: 'Personal overrides', value: status.personalOverrides },
              { label: 'Saved drafts', value: status.drafts },
            ]}
          />
        </>
      )}
    </OverviewCard>
  );
}

export function UsageCard() {
  const resource = useScopedResource(loadSystemUsage);
  return (
    <OverviewCard title="AI usage" to="/admin/llm" icon="gauge" resource={resource}>
      {(usage) => (
        <>
          {usage.site === null ? (
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Figure value="None" caption="site-wide allowance" />
              <StatusPill tone="neutral">Recording only</StatusPill>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-xs text-muted">
                Site-wide {usage.site.policy.period} allowance, resets{' '}
                {formatUtc(usage.site.period_end)}
              </p>
              <UsageBar
                label="Requests"
                used={usage.site.used_requests + usage.site.reserved_requests}
                limit={usage.site.request_limit}
              />
              <UsageBar
                label="Tokens"
                used={usage.site.used_tokens + usage.site.reserved_tokens}
                limit={usage.site.token_limit}
              />
            </div>
          )}
          <StatList
            items={[
              { label: 'System requests', value: compactNumber(usage.systemRequests) },
              { label: 'System tokens', value: compactNumber(usage.systemTokens) },
              { label: 'Unconfirmed calls', value: usage.unknownCalls },
            ]}
          />
          {usage.unknownCalls > 0 ? (
            <p className="mt-3 text-xs text-amber">
              Unconfirmed calls remain charged until their usage is reviewed.
            </p>
          ) : null}
        </>
      )}
    </OverviewCard>
  );
}
