/** Shared presentation of AI allowances and observed usage for account, team and admin views. */
import type { AiScope, AiUsageSummary, AiUsageTotals } from '@/lib/api/aiUsage';

const SCOPE_LABELS: Record<AiScope, string> = {
  global: 'Site-wide',
  system: 'System work',
  user: 'Personal',
  team: 'Team',
};

export function scopeLabel(scope: AiScope): string {
  return SCOPE_LABELS[scope];
}

export function percentage(used: number, limit: number | null): number | null {
  if (limit === null) return null;
  if (limit === 0) return 100;
  return Math.min(100, Math.round((used / limit) * 100));
}

export function UsageBar({
  label,
  used,
  limit,
}: {
  label: string;
  used: number;
  limit: number | null;
}) {
  const progress = percentage(used, limit);
  const blocked = limit === 0;
  return (
    <div>
      <div className="flex justify-between gap-2 text-sm">
        <span>{label}</span>
        <span className="text-muted">
          {blocked
            ? 'Blocked'
            : limit === null
              ? `${used.toLocaleString()} used`
              : `${used.toLocaleString()} / ${limit.toLocaleString()}`}
        </span>
      </div>
      {progress === null ? null : (
        <div
          className="mt-2 h-2 overflow-hidden rounded-full bg-line"
          role="progressbar"
          aria-label={`${label} used`}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progress}
        >
          <div
            className={`h-full ${progress >= 80 ? 'bg-amber' : 'bg-cyan'}`}
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );
}

export function AllowanceCard({ item }: { item: AiUsageSummary }) {
  const requests = item.used_requests + item.reserved_requests;
  const tokens = item.used_tokens + item.reserved_tokens;
  const near =
    [percentage(requests, item.request_limit), percentage(tokens, item.token_limit)].some(
      (value) => value !== null && value >= 80,
    ) || item.request_limit === 0;
  return (
    <article className="border border-line bg-surface/50 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-medium">
          {scopeLabel(item.policy.scope)} · <span className="capitalize">{item.policy.period}</span>{' '}
          allowance
        </h3>
        <span className="text-xs text-muted">
          Resets {new Date(item.period_end).toLocaleString()}
        </span>
      </div>
      {item.override ? (
        <p className="mt-2 text-xs text-amber">
          Temporary override until {new Date(item.override.expires_at).toLocaleString()}
        </p>
      ) : null}
      {near ? (
        <p className="mt-2 text-xs text-amber" role="status">
          This allowance is nearly or fully used. Requests are refused once it is reached.
        </p>
      ) : null}
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <UsageBar label="Requests" used={requests} limit={item.request_limit} />
        <UsageBar label="Tokens" used={tokens} limit={item.token_limit} />
      </div>
    </article>
  );
}

export function ObservedTotals({ label, totals }: { label: string; totals: AiUsageTotals }) {
  return (
    <p className="text-sm text-muted">
      <span className="font-medium text-text">{label}:</span>{' '}
      {totals.used_requests.toLocaleString()} requests, {totals.used_tokens.toLocaleString()} tokens
      this month
      {totals.unknown_requests > 0 ? `, ${totals.unknown_requests} with unconfirmed usage` : ''}.
    </p>
  );
}
