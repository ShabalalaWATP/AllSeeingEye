import { useState } from 'react';

import { describeError } from '@/lib/api/errors';
import { getTeamAiUsage, type AiUsageSummary } from '@/lib/api/aiUsage';

export function TeamAllowance({ teamId }: { teamId: string }) {
  const [items, setItems] = useState<AiUsageSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await getTeamAiUsage(teamId));
    } catch (reason) {
      setError(describeError(reason));
    } finally {
      setLoading(false);
    }
  };
  const rows = items ?? [];

  return (
    <details
      className="border border-line/70 bg-surface/40 p-5"
      onToggle={(event) => {
        if (event.currentTarget.open && items === null && !loading) void load();
      }}
    >
      <summary className="cursor-pointer text-sm font-semibold">AI allowance</summary>
      <div className="mt-4">
        {loading ? <p className="text-sm text-muted">Loading allowance…</p> : null}
        {error ? <p className="text-sm text-critical">{error}</p> : null}
        {items !== null && rows.length === 0 ? (
          <p className="text-sm text-muted">No allowance policy is active for this workspace.</p>
        ) : null}
        {rows.length > 0 ? (
          <ul className="grid gap-3 sm:grid-cols-2">
            {rows.map((item) => {
              const requestLimit = item.policy.request_limit;
              const tokenLimit = item.policy.token_limit;
              return (
                <li key={item.policy.id} className="border border-line/70 p-3 text-sm">
                  <p className="font-medium capitalize">
                    {item.policy.scope} · {item.policy.period}
                  </p>
                  <p className="mt-1 text-muted">
                    Requests: {item.used_requests}
                    {requestLimit === null ? ' / unlimited' : ` / ${requestLimit}`}
                  </p>
                  <p className="text-muted">
                    Tokens: {item.used_tokens.toLocaleString()}
                    {tokenLimit === null ? ' / unlimited' : ` / ${tokenLimit.toLocaleString()}`}
                  </p>
                </li>
              );
            })}
          </ul>
        ) : null}
      </div>
    </details>
  );
}
