/** Dated temporary overrides for one policy: explicit inherit, limit, unlimited or blocked states. */
import { useEffect, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import {
  createAiOverride,
  listAiOverrides,
  revokeAiOverride,
  type AiLimitState,
  type AiOverride,
  type AiPolicy,
} from '@/lib/api/aiUsage';
import { asApiError, describeError } from '@/lib/api/errors';

import { describeOverrideLimit, LIMIT_STATE_OPTIONS, parseLimit } from './aiUsagePresentation';

function localInput(date: Date): string {
  const shifted = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return shifted.toISOString().slice(0, 16);
}

function limitInput(state: AiLimitState, value: string): { state: AiLimitState; value?: number } {
  if (state !== 'limit') return { state };
  return { state, value: parseLimit(value) ?? Number.NaN };
}

export function AiPolicyOverrides({
  policy,
  label,
  onBusyChange,
  disabled = false,
}: {
  policy: AiPolicy;
  label: string;
  onBusyChange?: (busy: boolean) => void;
  disabled?: boolean;
}) {
  const [items, setItems] = useState<AiOverride[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [requestState, setRequestState] = useState<AiLimitState>('inherit');
  const [requestValue, setRequestValue] = useState('');
  const [tokenState, setTokenState] = useState<AiLimitState>('inherit');
  const [tokenValue, setTokenValue] = useState('');
  const [from, setFrom] = useState(() => localInput(new Date()));
  const [until, setUntil] = useState(() => localInput(new Date(Date.now() + 7 * 86_400_000)));

  useEffect(() => {
    let current = true;
    listAiOverrides(policy.id)
      .then((rows) => {
        if (current) setItems(rows);
      })
      .catch((caught: unknown) => {
        if (current) setError(describeError(asApiError(caught)));
      });
    return () => {
      current = false;
    };
  }, [policy.id]);

  async function create() {
    if (busy || disabled) return;
    const requests = limitInput(requestState, requestValue);
    const tokens = limitInput(tokenState, tokenValue);
    if (Number.isNaN(requests.value) || Number.isNaN(tokens.value)) {
      setError('An explicit override limit must be a whole number; zero blocks.');
      return;
    }
    const start = new Date(from);
    const end = new Date(until);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end <= start) {
      setError('Choose an end time after the start time.');
      return;
    }
    setBusy(true);
    onBusyChange?.(true);
    setError(null);
    try {
      const saved = await createAiOverride(policy.id, {
        requests,
        tokens,
        effective_from: start.toISOString(),
        expires_at: end.toISOString(),
      });
      setItems((current) => [saved, ...(current ?? [])]);
    } catch (caught) {
      setError(describeError(asApiError(caught)));
    } finally {
      setBusy(false);
      onBusyChange?.(false);
    }
  }

  async function revoke(item: AiOverride) {
    if (busy || disabled) return;
    setBusy(true);
    onBusyChange?.(true);
    setError(null);
    try {
      const revoked = await revokeAiOverride(item.id);
      setItems((current) => (current ?? []).map((row) => (row.id === item.id ? revoked : row)));
    } catch (caught) {
      setError(describeError(asApiError(caught)));
    } finally {
      setBusy(false);
      onBusyChange?.(false);
    }
  }

  return (
    <section
      aria-label={`Temporary overrides for ${label}`}
      className="space-y-3 border border-line/70 p-4"
    >
      <h3 className="text-sm font-semibold">Temporary overrides · {label}</h3>
      <p className="text-xs leading-5 text-muted">
        An active override replaces this policy&apos;s limits until it expires. The newest active
        override wins. Zero blocks; it never means unlimited.
      </p>
      {error ? <Alert tone="error">{error}</Alert> : null}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <SelectField
          label="Request override"
          value={requestState}
          disabled={busy || disabled}
          options={[...LIMIT_STATE_OPTIONS]}
          onChange={(event) => setRequestState(event.target.value as AiLimitState)}
        />
        {requestState === 'limit' ? (
          <TextField
            label="Request limit"
            inputMode="numeric"
            value={requestValue}
            disabled={busy || disabled}
            onChange={(event) => setRequestValue(event.target.value)}
          />
        ) : null}
        <SelectField
          label="Token override"
          value={tokenState}
          disabled={busy || disabled}
          options={[...LIMIT_STATE_OPTIONS]}
          onChange={(event) => setTokenState(event.target.value as AiLimitState)}
        />
        {tokenState === 'limit' ? (
          <TextField
            label="Token limit"
            inputMode="numeric"
            value={tokenValue}
            disabled={busy || disabled}
            onChange={(event) => setTokenValue(event.target.value)}
          />
        ) : null}
        <TextField
          label="Starts"
          type="datetime-local"
          value={from}
          disabled={busy || disabled}
          onChange={(event) => setFrom(event.target.value)}
        />
        <TextField
          label="Expires"
          type="datetime-local"
          value={until}
          disabled={busy || disabled}
          onChange={(event) => setUntil(event.target.value)}
        />
      </div>
      <Button variant="secondary" busy={busy} disabled={disabled} onClick={() => void create()}>
        Add override
      </Button>
      {items === null && error === null ? <LoadingNote label="Loading overrides" /> : null}
      {items?.length === 0 ? <p className="text-sm text-muted">No overrides recorded.</p> : null}
      {items && items.length > 0 ? (
        <ul className="divide-y divide-line text-sm" aria-label="Recorded overrides">
          {items.map((item) => (
            <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <span>
                Requests {describeOverrideLimit(item.requests.state, item.requests.value)} · Tokens{' '}
                {describeOverrideLimit(item.tokens.state, item.tokens.value)}
                <span className="block text-xs text-muted">
                  {new Date(item.effective_from).toLocaleString()} to{' '}
                  {new Date(item.expires_at).toLocaleString()}
                  {item.revoked_at ? ' · revoked' : ''}
                </span>
              </span>
              {item.revoked_at === null ? (
                <Button
                  variant="ghost"
                  disabled={busy || disabled}
                  onClick={() => void revoke(item)}
                >
                  Revoke
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
