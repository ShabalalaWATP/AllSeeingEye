import { useEffect, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import { asApiError, describeError } from '@/lib/api/errors';
import type { User } from '@/lib/api/schemas';
import {
  createAiPolicy,
  disableAiPolicy,
  listAiPolicies,
  previewAiUsage,
  updateAiPolicy,
  type AiPeriod,
  type AiPolicy,
  type AiPolicyInput,
  type AiScope,
  type AiUsageSummary,
} from '@/lib/api/aiUsage';
import type { Team } from '@/lib/api/teams';

function parseLimit(value: string): number | null {
  if (value.trim() === '') return null;
  const number = Number(value);
  return Number.isSafeInteger(number) && number >= 0 ? number : Number.NaN;
}

function policyLabel(policy: AiPolicy, users: readonly User[], teams: readonly Team[]): string {
  if (policy.scope === 'global') return 'Everyone';
  const target = policy.target_id;
  if (target === null) return policy.scope;
  if (policy.scope === 'user') {
    const user = users.find((item) => item.id === target);
    return user === undefined ? `User · ${target}` : `User · ${user.display_name} (${user.email})`;
  }
  const team = teams.find((item) => item.id === target);
  return team === undefined ? `Team · ${target}` : `Team · ${team.name}`;
}

export function AiUsagePolicies({
  users,
  teams,
}: {
  users: readonly User[];
  teams: readonly Team[];
}) {
  const [policies, setPolicies] = useState<AiPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scope, setScope] = useState<AiScope>('global');
  const [target, setTarget] = useState('');
  const [period, setPeriod] = useState<AiPeriod>('month');
  const [requests, setRequests] = useState('');
  const [tokens, setTokens] = useState('');
  const [editing, setEditing] = useState<AiPolicy | null>(null);
  const [previewUser, setPreviewUser] = useState('');
  const [previewTeam, setPreviewTeam] = useState('');
  const [previewRows, setPreviewRows] = useState<AiUsageSummary[] | null>(null);
  const [previewBusy, setPreviewBusy] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setPolicies(await listAiPolicies());
    } catch (caught) {
      setError(describeError(asApiError(caught)));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // This panel is mounted only when an administrator opens Usage controls.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, []);

  function resetForm() {
    setEditing(null);
    setScope('global');
    setTarget('');
    setPeriod('month');
    setRequests('');
    setTokens('');
  }

  function edit(policy: AiPolicy) {
    setEditing(policy);
    setScope(policy.scope);
    setTarget(policy.target_id ?? '');
    setPeriod(policy.period);
    setRequests(policy.request_limit === null ? '' : String(policy.request_limit));
    setTokens(policy.token_limit === null ? '' : String(policy.token_limit));
  }

  async function save() {
    if (busy) return;
    const requestLimit = parseLimit(requests);
    const tokenLimit = parseLimit(tokens);
    if (Number.isNaN(requestLimit) || Number.isNaN(tokenLimit)) {
      setError('Limits must be whole numbers, zero or blank for unlimited.');
      return;
    }
    if (scope !== 'global' && !target) {
      setError('Choose the user or team this policy should cover.');
      return;
    }
    const input: AiPolicyInput = {
      scope,
      ...(scope === 'global' ? {} : { target_id: target.trim() }),
      period,
      request_limit: requestLimit,
      token_limit: tokenLimit,
      enabled: true,
    };
    setBusy(true);
    setError(null);
    try {
      const saved = editing ? await updateAiPolicy(editing.id, input) : await createAiPolicy(input);
      setPolicies((current) => {
        const without = current.filter((item) => item.id !== saved.id);
        return [...without, saved].sort((a, b) => a.scope.localeCompare(b.scope));
      });
      resetForm();
    } catch (caught) {
      setError(describeError(asApiError(caught)));
    } finally {
      setBusy(false);
    }
  }

  async function disable(policy: AiPolicy) {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await disableAiPolicy(policy.id);
      setPolicies((current) => current.filter((item) => item.id !== policy.id));
      if (editing?.id === policy.id) resetForm();
    } catch (caught) {
      setError(describeError(asApiError(caught)));
    } finally {
      setBusy(false);
    }
  }

  async function preview() {
    if (!previewUser || previewBusy) return;
    setPreviewBusy(true);
    setError(null);
    try {
      setPreviewRows(await previewAiUsage(previewUser, previewTeam || undefined));
    } catch (caught) {
      setError(describeError(asApiError(caught)));
      setPreviewRows(null);
    } finally {
      setPreviewBusy(false);
    }
  }

  return (
    <section aria-label="AI access and usage" className="space-y-5 border-t border-line pt-6">
      <header>
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-ember">
          AI access &amp; usage
        </p>
        <h2 className="mt-2 text-lg font-semibold">Allowance policies</h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Policies apply to new provider calls. A blank limit is unlimited, while zero blocks the
          call. Personal requests use global and user policies; a team policy is charged only when
          work is explicitly assigned to that team.
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
      <div className="grid gap-3 border border-line bg-surface/50 p-4 sm:grid-cols-2 lg:grid-cols-6">
        <SelectField
          label="Scope"
          value={scope}
          disabled={busy}
          options={[
            { value: 'global', label: 'Everyone' },
            { value: 'user', label: 'User' },
            { value: 'team', label: 'Team' },
          ]}
          onChange={(event) => {
            setScope(event.target.value as AiScope);
            setTarget('');
          }}
        />
        {scope !== 'global' ? (
          <SelectField
            label={scope === 'user' ? 'Account' : 'Team'}
            value={target}
            disabled={busy}
            options={[
              { value: '', label: scope === 'user' ? 'Choose an account' : 'Choose a team' },
              ...(scope === 'user'
                ? users.map((user) => ({
                    value: user.id,
                    label: `${user.display_name} · ${user.email}`,
                  }))
                : teams.map((team) => ({ value: team.id, label: team.name }))),
              ...(target !== ''
                ? scope === 'user' && !users.some((user) => user.id === target)
                  ? [{ value: target, label: `Unavailable account · ${target}` }]
                  : scope === 'team' && !teams.some((team) => team.id === target)
                    ? [{ value: target, label: `Unavailable team · ${target}` }]
                    : []
                : []),
            ]}
            onChange={(event) => setTarget(event.target.value)}
          />
        ) : null}
        <SelectField
          label="Reset"
          value={period}
          disabled={busy}
          options={[
            { value: 'day', label: 'Daily' },
            { value: 'week', label: 'Weekly' },
            { value: 'month', label: 'Monthly' },
          ]}
          onChange={(event) => setPeriod(event.target.value as AiPeriod)}
        />
        <TextField
          label="Requests"
          inputMode="numeric"
          placeholder="Unlimited"
          value={requests}
          disabled={busy}
          onChange={(event) => setRequests(event.target.value)}
        />
        <TextField
          label="Tokens"
          inputMode="numeric"
          placeholder="Unlimited"
          value={tokens}
          disabled={busy}
          onChange={(event) => setTokens(event.target.value)}
        />
        <div className="flex items-end gap-2">
          <Button busy={busy} onClick={() => void save()}>
            {editing ? 'Save policy' : 'Add policy'}
          </Button>
          {editing ? (
            <Button variant="ghost" disabled={busy} onClick={resetForm}>
              Cancel
            </Button>
          ) : null}
        </div>
      </div>
      {loading ? <LoadingNote label="Loading allowance policies" /> : null}
      {!loading && policies.length === 0 ? (
        <p className="text-sm text-muted">
          No policies are active. Existing app budgets remain in effect.
        </p>
      ) : null}
      {!loading && policies.length > 0 ? (
        <div className="overflow-x-auto border border-line">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Active AI allowance policies</caption>
            <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="px-3 py-3">Scope</th>
                <th className="px-3 py-3">Reset</th>
                <th className="px-3 py-3">Requests</th>
                <th className="px-3 py-3">Tokens</th>
                <th className="px-3 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {policies.map((policy) => (
                <tr key={policy.id}>
                  <td className="px-3 py-3">
                    <span className="font-medium">{policyLabel(policy, users, teams)}</span>
                    <span className="block text-xs text-muted">Revision {policy.revision}</span>
                  </td>
                  <td className="px-3 py-3 capitalize">{policy.period}</td>
                  <td className="px-3 py-3">{policy.request_limit ?? 'Unlimited'}</td>
                  <td className="px-3 py-3">{policy.token_limit ?? 'Unlimited'}</td>
                  <td className="px-3 py-3">
                    <div className="flex gap-1">
                      <Button variant="ghost" disabled={busy} onClick={() => edit(policy)}>
                        Edit
                      </Button>
                      <Button variant="danger" disabled={busy} onClick={() => void disable(policy)}>
                        Disable
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      <section className="space-y-3 border-t border-line pt-5" aria-labelledby="ai-policy-preview">
        <div>
          <h3 id="ai-policy-preview" className="text-sm font-semibold">
            Preview effective allowance
          </h3>
          <p className="mt-1 text-xs leading-5 text-muted">
            Check which active policies would apply before assigning a user to a team task.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <SelectField
            label="Account"
            value={previewUser}
            disabled={previewBusy}
            options={[
              { value: '', label: 'Choose an account' },
              ...users.map((user) => ({
                value: user.id,
                label: `${user.display_name} · ${user.email}`,
              })),
            ]}
            onChange={(event) => {
              setPreviewUser(event.target.value);
              setPreviewRows(null);
            }}
          />
          <SelectField
            label="Destination (optional)"
            value={previewTeam}
            disabled={previewBusy}
            options={[
              { value: '', label: 'Personal workspace' },
              ...teams.map((team) => ({ value: team.id, label: team.name })),
            ]}
            onChange={(event) => {
              setPreviewTeam(event.target.value);
              setPreviewRows(null);
            }}
          />
          <div className="flex items-end">
            <Button
              variant="secondary"
              busy={previewBusy}
              disabled={!previewUser}
              onClick={() => void preview()}
            >
              Preview allowance
            </Button>
          </div>
        </div>
        {previewRows !== null ? (
          previewRows.length === 0 ? (
            <p className="text-sm text-muted">No active policy applies to this destination.</p>
          ) : (
            <ul className="grid gap-3 sm:grid-cols-2">
              {previewRows.map((item) => (
                <li key={item.policy.id} className="border border-line/70 p-3 text-sm">
                  <p className="font-medium capitalize">
                    {item.policy.scope} · {item.policy.period}
                  </p>
                  <p className="mt-1 text-muted">
                    {item.remaining_requests === null
                      ? 'Requests unlimited'
                      : `${item.remaining_requests} requests remaining`}
                    {' · '}
                    {item.remaining_tokens === null
                      ? 'tokens unlimited'
                      : `${item.remaining_tokens.toLocaleString()} tokens remaining`}
                  </p>
                </li>
              ))}
            </ul>
          )
        ) : null}
      </section>
    </section>
  );
}
