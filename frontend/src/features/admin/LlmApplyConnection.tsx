import { useEffect, useRef, useState } from 'react';

import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import type { LlmProfile } from '@/lib/api/llm';
import type { Team } from '@/lib/api/teams';

export interface LlmApplyConnectionProps {
  profile: LlmProfile;
  teams: readonly Team[];
  busy: boolean;
  hasGlobal: boolean;
  onApply: (teamId: string | null) => void;
}

/** Applying is a separate deliberate action after the saved revision passes a test. */
export function LlmApplyConnection({
  profile,
  teams,
  busy,
  hasGlobal,
  onApply,
}: LlmApplyConnectionProps) {
  const [scope, setScope] = useState('global');
  const [confirming, setConfirming] = useState(false);
  const confirmButton = useRef<HTMLButtonElement>(null);
  const audience =
    scope === 'global'
      ? 'Personal research and teams without an override'
      : teams.find((team) => team.id === scope)?.name;
  useEffect(() => {
    if (confirming) confirmButton.current?.focus();
  }, [confirming]);
  return (
    <div className="space-y-3 border-t border-line pt-4">
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
        ]}
      />
      {!hasGlobal && (
        <p className="text-xs text-muted">
          Apply a global connection before adding team overrides.
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
              ? 'Research planning, report writing, evidence review and shared feed translation will use this connection. Existing team overrides keep their current connection.'
              : 'Research planning, report writing and evidence review will use this connection. Shared feed translation keeps the global connection. Other teams and personal research keep their current connections.'}
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              ref={confirmButton}
              type="button"
              disabled={busy || audience === undefined}
              className="rounded-md bg-ember px-3 py-2 text-sm font-medium text-ground disabled:opacity-50"
              onClick={() => onApply(scope === 'global' ? null : scope)}
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
