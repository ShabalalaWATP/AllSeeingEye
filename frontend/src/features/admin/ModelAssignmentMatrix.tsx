import { useRef, useState } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import type { AiPolicy } from '@/lib/api/aiUsage';
import { describeError } from '@/lib/api/errors';
import type { LlmConnection, LlmProfile } from '@/lib/api/llm';
import type { User } from '@/lib/api/schemas';
import type { Team } from '@/lib/api/teams';

import { ModelAssignmentMatrixRow, type AssignmentAudience } from './ModelAssignmentMatrixRow';
import type { AllowancePreset } from './modelAllowancePresets';

export type { AllowancePreset } from './modelAllowancePresets';

/** Omitted values stay unchanged. A null model removes a team or personal override. */
export interface ModelAssignmentChange {
  scope: 'global' | 'team' | 'user';
  targetId: string | null;
  modelId?: string | null;
  preset?: AllowancePreset;
}

export interface ModelAssignmentMatrixProps {
  profiles: readonly LlmProfile[];
  connections: readonly LlmConnection[];
  policies: readonly AiPolicy[];
  teams: readonly Team[];
  users: readonly User[];
  busy: boolean;
  onSave: (change: ModelAssignmentChange) => Promise<void>;
}

function connectionFor(audience: AssignmentAudience, connections: readonly LlmConnection[]) {
  return connections.find((connection) => {
    if (audience.scope === 'team') return connection.team_id === audience.targetId;
    if (audience.scope === 'user') return connection.user_id === audience.targetId;
    return connection.team_id === null && !connection.user_id;
  });
}

const site: AssignmentAudience = {
  scope: 'global',
  targetId: null,
  name: 'Global / site',
  detail: 'Default model and shared site cap',
};

export function ModelAssignmentMatrix({
  profiles,
  connections,
  policies,
  teams,
  users,
  busy,
  onSave,
}: ModelAssignmentMatrixProps) {
  const [view, setView] = useState<'team' | 'user'>('team');
  const [search, setSearch] = useState('');
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const saving = useRef(false);
  const globalConnection = connectionFor(site, connections);
  const defaultName =
    profiles.find((profile) => profile.id === globalConnection?.profile_id)?.name ??
    'not configured';
  const activeTeams = teams.filter((team) => team.is_active);
  const activeUsers = users.filter((user) => user.is_active);
  const query = search.trim().toLocaleLowerCase('en-GB');
  const audiences: AssignmentAudience[] =
    view === 'team'
      ? activeTeams.map((team) => ({
          scope: 'team',
          targetId: team.id,
          name: team.name,
          detail: 'Team model and shared team cap',
        }))
      : activeUsers.map((user) => ({
          scope: 'user',
          targetId: user.id,
          name: user.display_name,
          detail: user.email,
        }));
  const matching = audiences.filter((audience) =>
    `${audience.name} ${audience.detail}`.toLocaleLowerCase('en-GB').includes(query),
  );
  const profileRevisions = profiles.map((profile) => [
    profile.id,
    profile.revision,
    profile.is_tested,
    profile.roles,
  ]);

  async function save(change: ModelAssignmentChange, name: string) {
    if (busy || saving.current) return;
    saving.current = true;
    setPending(`${change.scope}:${change.targetId ?? ''}`);
    setError(null);
    try {
      await onSave(change);
    } catch (caught) {
      // Keep errors outside revision-keyed rows, including a stale-write error after reload.
      setError(`${name}: ${describeError(caught)}`);
    } finally {
      saving.current = false;
      setPending(null);
    }
  }

  return (
    <section aria-labelledby="model-assignments-heading" className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 id="model-assignments-heading" className="text-lg font-semibold">
            Model assignments &amp; allowances
          </h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-muted">
            Set the site default, then choose models and daily caps for teams or users.
          </p>
        </div>
        <div className="flex gap-1" role="group" aria-label="Assignment audience">
          <Button
            variant={view === 'team' ? 'secondary' : 'ghost'}
            aria-pressed={view === 'team'}
            onClick={() => {
              setView('team');
              setSearch('');
            }}
          >
            Teams ({activeTeams.length})
          </Button>
          <Button
            variant={view === 'user' ? 'secondary' : 'ghost'}
            aria-pressed={view === 'user'}
            onClick={() => {
              setView('user');
              setSearch('');
            }}
          >
            Users ({activeUsers.length})
          </Button>
        </div>
      </header>
      <div className="max-w-sm">
        <TextField
          label={`Search ${view === 'team' ? 'teams' : 'users'}`}
          labelHidden
          type="search"
          placeholder={`Search ${view === 'team' ? 'teams' : 'users'}…`}
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </div>
      {error ? <Alert tone="error">{error}</Alert> : null}
      <div className="overflow-x-auto border-y border-line">
        <table className="w-full min-w-[760px] text-left text-sm">
          <caption className="sr-only">Models and daily allowances by audience</caption>
          <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
            <tr>
              <th scope="col" className="px-4 py-3">
                Audience
              </th>
              <th scope="col" className="px-4 py-3">
                Model
              </th>
              <th scope="col" className="px-4 py-3">
                Daily allowance
              </th>
              <th scope="col" className="px-4 py-3">
                <span className="sr-only">Save changes</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line/70">
            {[site, ...matching].map((audience) => {
              const connection = connectionFor(audience, connections);
              const rowPolicies = policies.filter(
                (policy) =>
                  policy.scope === audience.scope && policy.target_id === audience.targetId,
              );
              const rowId = `${audience.scope}:${audience.targetId ?? ''}`;
              // Drafts expire when authoritative assignments, policy revisions or model proof change.
              const revision = JSON.stringify([
                connection,
                rowPolicies,
                globalConnection,
                profileRevisions,
              ]);
              return (
                <ModelAssignmentMatrixRow
                  key={`${rowId}:${revision}`}
                  audience={audience}
                  connection={connection}
                  profiles={profiles}
                  defaultName={defaultName}
                  hasDefault={globalConnection !== undefined}
                  policies={rowPolicies}
                  busy={busy || pending !== null}
                  saving={pending === rowId}
                  onSave={save}
                />
              );
            })}
          </tbody>
        </table>
      </div>
      {matching.length === 0 ? (
        <p className="text-sm text-muted">
          {query
            ? 'No matches. Try another search.'
            : `No active ${view === 'team' ? 'teams' : 'users'} yet.`}
        </p>
      ) : null}
      <p className="max-w-4xl text-xs leading-5 text-muted">
        Site and team caps are shared. User caps cover all their requests, including team work; user
        model choices apply to personal work only. Weekly, monthly and temporary limits still apply.
        Use advanced usage controls to edit custom limits.
      </p>
    </section>
  );
}
