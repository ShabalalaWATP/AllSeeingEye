import { useEffect, useRef, useState } from 'react';

import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import type { LlmProfile } from '@/lib/api/llm';
import type { User } from '@/lib/api/schemas';
import type { Team } from '@/lib/api/teams';

export interface LlmApplyConnectionProps {
  profile: LlmProfile;
  teams: readonly Team[];
  users?: readonly User[];
  busy: boolean;
  initialScope?: string;
  hasGlobal: boolean;
  onApply: (teamId: string | null, userId?: string) => void;
}

/** Applying is a separate deliberate action after the saved revision passes a test. */
export function LlmApplyConnection({
  profile,
  teams,
  users = [],
  initialScope = 'global',
  busy,
  hasGlobal,
  onApply,
}: LlmApplyConnectionProps) {
  const [search, setSearch] = useState('');
  const [scope, setScope] = useState(initialScope);
  const [confirming, setConfirming] = useState(false);
  const container = useRef<HTMLDivElement>(null);
  useEffect(() => {
    container.current?.querySelector('select')?.focus();
  }, []);
  const confirmButton = useRef<HTMLButtonElement>(null);
  const audience =
    scope === 'global'
      ? 'Users and teams without an override'
      : scope.startsWith('user:')
        ? users.find((user) => user.id === scope.slice(5))?.email
        : teams.find((team) => team.id === scope)?.name;
  useEffect(() => {
    if (confirming) confirmButton.current?.focus();
  }, [confirming]);
  return (
    <div ref={container} className="space-y-3 border-t border-line pt-4">
      {users.length > 0 && hasGlobal && (
        <TextField
          label="Find a personal workspace"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      )}
      <SelectField
        label={`Apply ${profile.name} to`}
        value={scope}
        onChange={(event) => {
          setScope(event.target.value);
          setConfirming(false);
        }}
        disabled={busy}
        options={[
          { value: 'global', label: 'Global connection' },
          ...(hasGlobal
            ? teams
                .filter((team) => team.is_active)
                .map((team) => ({ value: team.id, label: team.name }))
            : []),
          ...(hasGlobal
            ? users
                .filter(
                  (user) =>
                    user.is_active &&
                    (scope === `user:${user.id}` ||
                      user.email.toLowerCase().includes(search.toLowerCase())),
                )
                .map((user) => ({
                  value: `user:${user.id}`,
                  label: `Personal workspace: ${user.email}`,
                }))
            : []),
        ]}
      />
      {!hasGlobal && (
        <p className="text-xs text-muted">
          Apply a global connection before adding team or personal overrides.
        </p>
      )}
      {confirming ? (
        <div role="group" aria-label="Confirm connection switch" className="space-y-3">
          <p className="text-sm">
            Switch <strong>{audience}</strong> to <strong>{profile.name}</strong>?
          </p>
          <p className="break-all text-sm">
            {profile.model}
            {profile.reasoning_effort && (
              <span className="capitalize"> · {profile.reasoning_effort} reasoning</span>
            )}
            <br />
            {profile.base_url}
            {profile.api_key_hint && <span> · Key ending {profile.api_key_hint}</span>}
          </p>
          <p className="text-xs text-muted">
            {scope === 'global'
              ? 'Research planning, report writing, evidence review and shared feed translation will use this connection. Existing team and personal overrides keep their current connection.'
              : scope.startsWith('user:')
                ? 'Only this personal workspace changes. Their team research uses the team or global connection. Shared feed translation keeps the global connection.'
                : 'Research planning, report writing and evidence review will use this connection. Shared feed translation keeps the global connection. Other teams and personal research keep their current connections.'}
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              ref={confirmButton}
              type="button"
              disabled={busy || audience === undefined}
              className="rounded-md bg-ember px-3 py-2 text-sm font-medium text-ground disabled:opacity-50"
              onClick={() =>
                scope.startsWith('user:')
                  ? onApply(null, scope.slice(5))
                  : onApply(scope === 'global' ? null : scope)
              }
            >
              {busy ? 'Applying…' : 'Confirm switch'}
            </button>
            <Button variant="ghost" disabled={busy} onClick={() => setConfirming(false)}>
              Keep current connection
            </Button>
          </div>
        </div>
      ) : (
        <Button onClick={() => setConfirming(true)} disabled={busy || audience === undefined}>
          Review and apply
        </Button>
      )}
    </div>
  );
}
