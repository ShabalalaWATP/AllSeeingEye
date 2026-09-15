import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import type { AiPeriod, AiPolicy, AiPolicyInput, AiScope } from '@/lib/api/aiUsage';
import type { User } from '@/lib/api/schemas';
import type { Team } from '@/lib/api/teams';

import { parseLimit } from './aiUsagePresentation';

const UNTARGETED: readonly AiScope[] = ['global', 'system'];

/** Create or edit one policy. Mount with a key per edited policy to reset its fields. */
export function AiPolicyForm({
  users,
  teams,
  editing,
  busy,
  onSave,
  onCancel,
  onInvalid,
}: {
  users: readonly User[];
  teams: readonly Team[];
  editing: AiPolicy | null;
  busy: boolean;
  onSave: (input: AiPolicyInput) => Promise<boolean>;
  onCancel: () => void;
  onInvalid: (message: string) => void;
}) {
  const [scope, setScope] = useState<AiScope>(editing?.scope ?? 'global');
  const [target, setTarget] = useState(editing?.target_id ?? '');
  const [period, setPeriod] = useState<AiPeriod>(editing?.period ?? 'month');
  const [requests, setRequests] = useState(
    editing?.request_limit == null ? '' : String(editing.request_limit),
  );
  const [tokens, setTokens] = useState(
    editing?.token_limit == null ? '' : String(editing.token_limit),
  );
  const targeted = !UNTARGETED.includes(scope);

  async function submit() {
    const requestLimit = parseLimit(requests);
    const tokenLimit = parseLimit(tokens);
    if (Number.isNaN(requestLimit) || Number.isNaN(tokenLimit)) {
      onInvalid('Limits must be whole numbers, zero or blank for unlimited.');
      return;
    }
    if (targeted && !target) {
      onInvalid('Choose the user or team this policy should cover.');
      return;
    }
    const saved = await onSave({
      scope,
      ...(targeted ? { target_id: target.trim() } : {}),
      period,
      request_limit: requestLimit,
      token_limit: tokenLimit,
      enabled: true,
    });
    if (saved && editing === null) {
      setScope('global');
      setTarget('');
      setRequests('');
      setTokens('');
    }
  }

  const targetOptions =
    scope === 'user'
      ? users.map((user) => ({ value: user.id, label: `${user.display_name} · ${user.email}` }))
      : teams.map((team) => ({ value: team.id, label: team.name }));
  const known = targetOptions.some((option) => option.value === target);

  return (
    <div className="grid gap-3 border border-line bg-surface/50 p-4 sm:grid-cols-2 lg:grid-cols-6">
      <SelectField
        label="Scope"
        value={scope}
        disabled={busy}
        options={[
          { value: 'global', label: 'Everyone' },
          { value: 'system', label: 'System work' },
          { value: 'user', label: 'User' },
          { value: 'team', label: 'Team' },
        ]}
        onChange={(event) => {
          setScope(event.target.value as AiScope);
          setTarget('');
        }}
      />
      {targeted ? (
        <SelectField
          label={scope === 'user' ? 'Account' : 'Team'}
          value={target}
          disabled={busy}
          options={[
            { value: '', label: scope === 'user' ? 'Choose an account' : 'Choose a team' },
            ...targetOptions,
            ...(target !== '' && !known
              ? [{ value: target, label: `Unavailable ${scope === 'user' ? 'account' : 'team'}` }]
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
        <Button busy={busy} onClick={() => void submit()}>
          {editing ? 'Save policy' : 'Add policy'}
        </Button>
        {editing ? (
          <Button variant="ghost" disabled={busy} onClick={onCancel}>
            Cancel
          </Button>
        ) : null}
      </div>
    </div>
  );
}
