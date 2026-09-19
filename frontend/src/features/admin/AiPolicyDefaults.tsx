/** Suggest, and only then apply, the documented starting set of allowance policies. */
import { useEffect, useState } from 'react';

import { spendOf } from '@/components/aiUsage/spend';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import {
  applyAiPolicyDefaults,
  getAiPolicyDefaults,
  type AiPolicy,
  type AiPolicyDefaults as Defaults,
} from '@/lib/api/aiUsage';
import { asApiError, describeError } from '@/lib/api/errors';

const PERIODS: Record<string, string> = { day: 'a day', week: 'a week', month: 'a month' };

export function AiPolicyDefaults({
  onApplied,
  onBusyChange,
  disabled = false,
}: {
  onApplied: (created: AiPolicy[]) => void;
  onBusyChange?: (busy: boolean) => void;
  disabled?: boolean;
}) {
  const [defaults, setDefaults] = useState<Defaults | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [applied, setApplied] = useState<number | null>(null);

  async function load() {
    setError(null);
    try {
      setDefaults(await getAiPolicyDefaults());
    } catch (caught) {
      setError(describeError(asApiError(caught)));
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, []);

  async function apply() {
    if (busy || disabled) return;
    setBusy(true);
    onBusyChange?.(true);
    setError(null);
    try {
      const created = await applyAiPolicyDefaults();
      setApplied(created.length);
      onApplied(created);
      await load();
    } catch (caught) {
      setError(describeError(asApiError(caught)));
    } finally {
      setBusy(false);
      onBusyChange?.(false);
    }
  }

  const missing = defaults?.items.filter((item) => !item.already_configured) ?? [];
  const daily = defaults?.observed_daily_tokens ?? 0;
  const suggestedDaily =
    defaults?.items.find((item) => item.scope === 'global' && item.period === 'day')?.token_limit ??
    0;

  return (
    <section
      aria-labelledby="ai-policy-defaults"
      className="space-y-3 rounded-lg border border-line/70 bg-ground/30 p-4"
    >
      <div>
        <h3 id="ai-policy-defaults" className="text-sm font-semibold">
          Suggested starting policies
        </h3>
        <p className="mt-1 text-xs leading-5 text-muted">
          Nothing is capped until a policy exists. These are a suggestion only: review the numbers,
          edit any of them afterwards, and apply them when you are ready.
        </p>
      </div>
      {error ? (
        <Alert tone="error">
          {error}{' '}
          <Button
            variant="ghost"
            aria-label="Retry loading suggested policies"
            disabled={busy || disabled}
            onClick={() => void load()}
          >
            Retry
          </Button>
        </Alert>
      ) : null}
      {defaults === null && error === null ? (
        <LoadingNote label="Loading suggested policies" />
      ) : null}
      {defaults ? (
        <>
          <p className="text-sm" role="status">
            {defaults.enforcing
              ? 'At least one policy is active, so AI requests can be refused when a limit is reached.'
              : 'No policy is active. Usage is recorded for observation and nothing is enforced.'}
          </p>
          <p className="text-xs leading-5 text-muted">
            This site has recorded {defaults.observed.used_tokens.toLocaleString()} tokens this
            month, about {daily.toLocaleString()} a day
            {spendOf(defaults.observed, defaults.prices)
              ? ` (${spendOf(defaults.observed, defaults.prices)} estimated)`
              : ''}
            .{' '}
            {suggestedDaily > 0 && daily > 0
              ? `The suggested site-wide daily ceiling of ${suggestedDaily.toLocaleString()} tokens is about ${(suggestedDaily / daily).toFixed(1)} times that average, so raise it before applying if you want more headroom.`
              : 'Raise any figure that looks tight for how you work.'}
          </p>
          <ul className="space-y-2 text-sm">
            {defaults.items.map((item) => (
              <li
                key={`${item.scope}:${item.target_id ?? 'none'}:${item.period}`}
                className="flex flex-wrap items-baseline justify-between gap-2 border-b border-line/50 pb-2 last:border-0"
              >
                <span>
                  <span className="font-medium">{item.target_name}</span>{' '}
                  <span className="text-muted">
                    · {item.token_limit.toLocaleString()} tokens {PERIODS[item.period] ?? ''}
                  </span>
                  <span className="block text-xs text-muted">{item.reason}</span>
                </span>
                <span className="text-xs text-muted">
                  {item.already_configured ? 'Already configured, kept as is' : 'Would be created'}
                </span>
              </li>
            ))}
          </ul>
          {applied === null ? null : (
            <p className="text-sm text-cyan" role="status">
              {applied === 0
                ? 'Every suggested policy already existed. Nothing was changed.'
                : `${applied} policies were created. Existing policies were left untouched.`}
            </p>
          )}
          <Button
            variant="secondary"
            busy={busy}
            disabled={disabled || missing.length === 0}
            onClick={() => void apply()}
          >
            {missing.length === 0
              ? 'All suggested policies exist'
              : `Apply ${missing.length} suggested policies`}
          </Button>
        </>
      ) : null}
    </section>
  );
}
