import { useCallback, useEffect, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import {
  createAiPolicy,
  disableAiPolicy,
  listAiPolicies,
  updateAiPolicy,
  type AiPolicy,
  type AiPolicyInput,
} from '@/lib/api/aiUsage';
import { asApiError, describeError } from '@/lib/api/errors';
import type { User } from '@/lib/api/schemas';
import { useConfirmedAction } from '@/lib/hooks/useConfirmedAction';
import type { Team } from '@/lib/api/teams';

import { AiPolicyDefaults } from './AiPolicyDefaults';
import { AiPolicyForm, type AiPolicyPrefill } from './AiPolicyForm';
import { AiPolicyOverrides } from './AiPolicyOverrides';
import { AiUsagePreview } from './AiUsagePreview';
import { policyLabel } from './aiUsagePresentation';

export function AiUsagePolicies({
  users,
  teams,
  onBusyChange,
}: {
  users: readonly User[];
  teams: readonly Team[];
  onBusyChange?: (busy: boolean) => void;
}) {
  const [policies, setPolicies] = useState<AiPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [defaultsBusy, setDefaultsBusy] = useState(false);
  const [overridesBusy, setOverridesBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<AiPolicy | null>(null);
  const [overridesFor, setOverridesFor] = useState<AiPolicy | null>(null);
  const [prefill, setPrefill] = useState<AiPolicyPrefill | null>(null);
  const disabling = useConfirmedAction(
    useCallback(async (policy: AiPolicy) => {
      await disableAiPolicy(policy.id);
      setPolicies((current) => current.filter((item) => item.id !== policy.id));
      setEditing((current) => (current?.id === policy.id ? null : current));
      setOverridesFor((current) => (current?.id === policy.id ? null : current));
    }, []),
  );
  const pending = busy || defaultsBusy || overridesBusy || disabling.busy;

  useEffect(() => {
    onBusyChange?.(pending);
  }, [pending, onBusyChange]);

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

  async function save(input: AiPolicyInput): Promise<boolean> {
    if (pending) return false;
    setBusy(true);
    setError(null);
    try {
      const saved = editing ? await updateAiPolicy(editing.id, input) : await createAiPolicy(input);
      setPolicies((current) =>
        [...current.filter((item) => item.id !== saved.id), saved].sort((a, b) =>
          a.scope.localeCompare(b.scope),
        ),
      );
      setEditing(null);
      setPrefill(null);
      return true;
    } catch (caught) {
      setError(describeError(asApiError(caught)));
      return false;
    } finally {
      setBusy(false);
    }
  }

  const active = policies.filter((policy) => policy.enabled);
  const target = disabling.target;

  return (
    <section aria-label="AI access and usage" className="space-y-5">
      <header>
        <p className="font-mono text-2xs uppercase tracking-[0.2em] text-ember">
          AI access &amp; usage
        </p>
        <h2 className="mt-2 text-lg font-semibold">Allowance policies</h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Policies apply to new provider calls. A blank limit is unlimited, while zero blocks the
          call. Personal requests use site-wide and user policies; a team policy is charged only
          when work is explicitly assigned to that team. Shared feed translation and screening use
          the system work policy. Usage is recorded even when no policy is active.
        </p>
      </header>
      {error ? (
        <Alert tone="error">
          {error}{' '}
          <Button variant="ghost" disabled={pending} onClick={() => void load()}>
            Retry
          </Button>
        </Alert>
      ) : null}
      <AiPolicyDefaults
        disabled={busy || overridesBusy}
        onBusyChange={setDefaultsBusy}
        onApplied={(created) =>
          setPolicies((current) => [
            ...current.filter((item) => !created.some((made) => made.id === item.id)),
            ...created,
          ])
        }
      />
      <AiPolicyForm
        key={`policy-form:${editing?.id ?? prefill?.targetId ?? 'new'}`}
        users={users}
        teams={teams}
        editing={editing}
        prefill={prefill ?? undefined}
        busy={pending}
        onSave={save}
        onCancel={() => {
          setEditing(null);
          setPrefill(null);
        }}
        onInvalid={setError}
      />
      {loading ? <LoadingNote label="Loading allowance policies" /> : null}
      {!loading && active.length === 0 ? (
        <p className="text-sm text-muted">
          No policies are active. Usage is recorded for observation and existing app budgets remain
          in effect.
        </p>
      ) : null}
      {!loading && active.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-line">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Active AI allowance policies</caption>
            <thead className="border-b border-line bg-surface-2/60 text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="px-3 py-3">Scope</th>
                <th className="px-3 py-3">Reset</th>
                <th className="px-3 py-3">Requests</th>
                <th className="px-3 py-3">Tokens</th>
                <th className="px-3 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {active.map((policy) => {
                const label = policyLabel(policy, users, teams);
                return (
                  <tr key={policy.id}>
                    <td className="px-3 py-3">
                      <span className="font-medium">{label}</span>
                      <span className="block text-xs text-muted">Revision {policy.revision}</span>
                    </td>
                    <td className="px-3 py-3 capitalize">{policy.period}</td>
                    <td className="px-3 py-3">{policy.request_limit ?? 'Unlimited'}</td>
                    <td className="px-3 py-3">{policy.token_limit ?? 'Unlimited'}</td>
                    <td className="px-3 py-3">
                      <div className="flex flex-wrap gap-1">
                        <Button
                          variant="ghost"
                          disabled={pending}
                          aria-label={`Edit ${label}`}
                          onClick={() => setEditing(policy)}
                        >
                          Edit
                        </Button>
                        <Button
                          variant="ghost"
                          disabled={pending}
                          aria-label={`Overrides for ${label}`}
                          onClick={() =>
                            setOverridesFor((current) =>
                              current?.id === policy.id ? null : policy,
                            )
                          }
                        >
                          Overrides
                        </Button>
                        <Button
                          variant="danger"
                          disabled={pending}
                          aria-label={`Disable ${label}`}
                          aria-haspopup="dialog"
                          onClick={() => disabling.ask(policy)}
                        >
                          Disable
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
      <ConfirmDialog
        open={target !== null}
        title={`Disable allowance policy “${target ? policyLabel(target, users, teams) : ''}”?`}
        confirmLabel="Disable policy"
        busyLabel="Disabling policy…"
        busy={disabling.busy}
        error={disabling.error === null ? null : describeError(disabling.error)}
        onCancel={disabling.cancel}
        onConfirm={disabling.confirm}
      >
        <p>
          Enforcement of this policy&apos;s request and token limits, and of its overrides, stops
          for new provider calls. Usage is still recorded.
        </p>
        {target !== null && active.every((policy) => policy.id === target.id) ? (
          <p className="font-medium text-critical">
            This is the last active policy, so no AI caps will apply once it is disabled.
          </p>
        ) : null}
      </ConfirmDialog>
      {overridesFor ? (
        <AiPolicyOverrides
          key={`policy-overrides:${overridesFor.id}`}
          policy={overridesFor}
          label={policyLabel(overridesFor, users, teams)}
          disabled={busy || defaultsBusy}
          onBusyChange={setOverridesBusy}
        />
      ) : null}
      <AiUsagePreview
        users={users}
        teams={teams}
        onEditLimit={(scope, targetId) => {
          if (pending) return;
          const existing = active.find(
            (item) => item.scope === scope && item.target_id === targetId,
          );
          setEditing(existing ?? null);
          setPrefill(existing ? null : { scope, targetId });
        }}
      />
    </section>
  );
}
