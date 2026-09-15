import { useEffect, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { asApiError, describeError } from '@/lib/api/errors';
import { getMyAiUsage, type AiUsageSummary as Usage } from '@/lib/api/aiUsage';

function percentage(used: number, reserved: number, limit: number | null): number | null {
  return limit === null ? null : Math.min(100, Math.round(((used + reserved) / limit) * 100));
}

export function AiUsageSummary() {
  const [items, setItems] = useState<Usage[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setError(null);
    try {
      setItems(await getMyAiUsage());
    } catch (caught) {
      setError(describeError(asApiError(caught)));
    }
  }

  useEffect(() => {
    // This page owns the request lifecycle, so changing settings never causes
    // a background usage poll across the rest of the application.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, []);

  return (
    <section aria-label="AI usage" className="flex max-w-2xl flex-col gap-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-widest text-cyan">Usage awareness</p>
        <h2 className="mt-2 text-xl font-semibold">AI allowance</h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          See the allowances that apply to your personal requests. Team work is counted against its
          explicitly selected team policy as well as any site-wide ceiling.
        </p>
      </header>
      {error ? (
        <Alert tone="error">
          {error}{' '}
          <Button variant="ghost" onClick={() => void load()}>
            Retry
          </Button>
        </Alert>
      ) : null}
      {items === null && error === null ? <LoadingNote label="Loading AI allowance" /> : null}
      {items?.length === 0 ? (
        <p className="text-sm text-muted">
          No administrator allowance is configured. Existing app budgets still apply.
        </p>
      ) : null}
      {items && items.length > 0 ? (
        <div className="flex flex-col gap-4">
          {items.map((item) => {
            const requestProgress = percentage(
              item.used_requests,
              item.reserved_requests,
              item.policy.request_limit,
            );
            const tokenProgress = percentage(
              item.used_tokens,
              item.reserved_tokens,
              item.policy.token_limit,
            );
            return (
              <article key={item.policy.id} className="border border-line bg-surface/50 p-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h3 className="font-medium capitalize">{item.policy.period} allowance</h3>
                  <span className="text-xs text-muted">
                    Resets {new Date(item.period_end).toLocaleString()}
                  </span>
                </div>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <UsageBar
                    label="Requests"
                    used={item.used_requests + item.reserved_requests}
                    limit={item.policy.request_limit}
                    progress={requestProgress}
                  />
                  <UsageBar
                    label="Tokens"
                    used={item.used_tokens + item.reserved_tokens}
                    limit={item.policy.token_limit}
                    progress={tokenProgress}
                  />
                </div>
              </article>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}

function UsageBar({
  label,
  used,
  limit,
  progress,
}: {
  label: string;
  used: number;
  limit: number | null;
  progress: number | null;
}) {
  return (
    <div>
      <div className="flex justify-between text-sm">
        <span>{label}</span>
        <span className="text-muted">{limit === null ? `${used} used` : `${used} / ${limit}`}</span>
      </div>
      {progress === null ? null : (
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-line">
          <div
            className={`h-full ${progress >= 80 ? 'bg-amber' : 'bg-cyan'}`}
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );
}
