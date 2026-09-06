import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import type { LlmProfile, LlmRole } from '@/lib/api/llm';
import type { Team } from '@/lib/api/teams';

import { ROLE_LABELS } from './llmPresentation';

export interface ConnectionSelection {
  profile: LlmProfile;
  roles: LlmRole[];
}
export interface LlmConnectionSummaryProps {
  global: readonly ConnectionSelection[];
  teams: readonly { team: Team; connections: ConnectionSelection[] }[];
  onReplace: (profile: LlmProfile) => void;
  onReuse: (profile: LlmProfile) => void;
  disabled: boolean;
  legacy: boolean;
  onReset: (team: Team) => void;
}

function Connection({
  selection,
  onReplace,
  onReuse,
  disabled,
}: {
  selection: ConnectionSelection;
  onReplace: (profile: LlmProfile) => void;
  onReuse: (profile: LlmProfile) => void;
  disabled: boolean;
}) {
  const profile = selection.profile;
  return (
    <div className="flex min-w-0 flex-wrap items-start justify-between gap-3 py-3">
      <div className="min-w-0 space-y-1">
        <p className="break-words font-medium">{profile.name}</p>
        <p className="break-all font-mono text-sm text-muted">
          {profile.model}
          {profile.reasoning_effort && (
            <span className="ml-2 capitalize text-text">
              · {profile.reasoning_effort} reasoning
            </span>
          )}
        </p>
        <p className="text-xs text-muted">
          {selection.roles.map((role) => ROLE_LABELS[role]).join(' · ')}
        </p>
        <p className="break-all text-xs text-muted">{profile.base_url}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {profile.is_bound && (
          <Button
            variant="ghost"
            disabled={disabled}
            onClick={() => onReuse(profile)}
            aria-label={`Reuse ${profile.name}`}
          >
            Use for another scope
          </Button>
        )}
        <Button
          variant="secondary"
          disabled={disabled}
          onClick={() => onReplace(profile)}
          aria-label={`Replace ${profile.name}`}
        >
          Replace connection
        </Button>
      </div>
    </div>
  );
}

/** Grouped routing, so the operator can see which audience a change will affect. */
export function LlmConnectionSummary({
  global,
  teams,
  onReplace,
  onReuse,
  disabled,
  legacy,
  onReset,
}: LlmConnectionSummaryProps) {
  const [resetTeam, setResetTeam] = useState<string | null>(null);
  return (
    <div className="space-y-7">
      <section aria-label="Global AI connection" className="border-t border-line pt-5">
        <h2 className="text-base font-semibold">
          {legacy ? 'Current role-based connections' : 'Global connection'}
        </h2>
        <p className="mt-1 text-sm text-muted">
          {legacy
            ? 'Existing role selection remains in use until a tested global connection is applied.'
            : 'Used for personal research and teams without an override.'}
        </p>
        {global.length === 0 ? (
          <p className="mt-4 text-sm text-muted">
            No global connection is active. Save and test a draft to configure one.
          </p>
        ) : (
          <div className="mt-2 divide-y divide-line">
            {global.map((selection) => (
              <Connection
                key={selection.profile.id}
                selection={selection}
                onReplace={onReplace}
                onReuse={onReuse}
                disabled={disabled}
              />
            ))}
          </div>
        )}
      </section>
      <section aria-label="Team AI overrides" className="border-t border-line pt-5">
        <h2 className="text-base font-semibold">Team overrides</h2>
        <p className="mt-1 text-sm text-muted">
          These connections keep their own model when the global connection changes.
        </p>
        {teams.length === 0 ? (
          <p className="mt-4 text-sm text-muted">
            No team overrides. Teams use the global connection.
          </p>
        ) : (
          <ul className="mt-4 divide-y divide-line">
            {teams.map(({ team, connections }) => (
              <li key={team.id} className="py-4 first:pt-0">
                <h3 className="text-sm font-semibold">
                  {team.name}
                  {!team.is_active && <span className="ml-2 font-normal text-muted">Archived</span>}
                </h3>
                {connections.map((selection) => (
                  <Connection
                    key={selection.profile.id}
                    selection={selection}
                    onReplace={onReplace}
                    onReuse={onReuse}
                    disabled={disabled}
                  />
                ))}
                {resetTeam === team.id ? (
                  <div className="space-y-2">
                    <p className="text-sm">Use the global connection for {team.name}?</p>
                    <div className="flex flex-wrap gap-2">
                      <Button variant="secondary" disabled={disabled} onClick={() => onReset(team)}>
                        Confirm use global
                      </Button>
                      <Button
                        variant="ghost"
                        disabled={disabled}
                        onClick={() => setResetTeam(null)}
                      >
                        Keep override
                      </Button>
                    </div>
                  </div>
                ) : (
                  <Button variant="ghost" disabled={disabled} onClick={() => setResetTeam(team.id)}>
                    Use global connection
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
