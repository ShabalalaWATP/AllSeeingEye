import { useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import { describeError } from '@/lib/api/errors';
import type { User } from '@/lib/api/schemas';
import { createTeam, listTeams } from '@/lib/api/teams';
import { useAuthStore } from '@/stores/auth';

import { TeamNameForm } from './TeamForms';
import { TeamPanel } from './TeamPanel';
import { TeamInvitationInbox } from './TeamInvitationInbox';
import { useTeamAction, useTeamsResource } from './useTeams';

function isAccessError(status: number, code: string): boolean {
  return status === 401 || status === 403 || ['forbidden', 'session_expired'].includes(code);
}

function CreationPanel({
  open,
  busy,
  onOpen,
  onSave,
}: {
  open: boolean;
  busy: boolean;
  onOpen: () => void;
  onSave: (name: string, description?: string) => void;
}) {
  if (!open) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-4 border border-line/70 bg-surface/50 px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold">Start a shared workspace</h2>
          <p className="mt-1 text-sm text-muted">
            Every account can create a team and becomes its first manager automatically.
          </p>
        </div>
        <Button variant="secondary" onClick={onOpen} aria-expanded={false}>
          Create a team
        </Button>
      </div>
    );
  }
  return (
    <div className="border border-ember/50 bg-surface/60 px-5 py-5" id="create-team-panel">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <p className="font-mono text-2xs uppercase tracking-[0.2em] text-ember">New workspace</p>
          <h2 className="mt-1 text-base font-semibold">Name your team</h2>
          <p className="mt-1 text-sm text-muted">
            You will be added as its first team manager when it is created.
          </p>
        </div>
        <Button variant="ghost" disabled={busy} onClick={onOpen} aria-expanded={true}>
          Cancel
        </Button>
      </div>
      <TeamNameForm busy={busy} onSave={onSave} />
    </div>
  );
}

function EmptyTeams({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="border border-dashed border-line bg-surface/30 px-6 py-10 text-center">
      <p className="font-mono text-2xs uppercase tracking-[0.2em] text-ember">No workspaces yet</p>
      <h2 className="mt-2 text-xl font-semibold">Create your first team</h2>
      <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-muted">
        Teams are small shared workspaces for research, reports, and short operational context. The
        account that creates one is its first manager.
      </p>
      <Button className="mt-5" onClick={onCreate}>
        Create a team
      </Button>
    </div>
  );
}

function TeamsWorkspace({ user }: { user: User }) {
  const resource = useTeamsResource(listTeams);
  const action = useTeamAction();
  const [selected, setSelected] = useState('');
  const [creating, setCreating] = useState(false);
  const teams = resource.data;
  const teamId = teams?.find((team) => team.id === selected)?.id ?? teams?.[0]?.id;

  const submitTeam = (name: string, description?: string) => {
    void action.run(
      async () => {
        const team = await createTeam(name, description);
        setSelected(team.id);
        setCreating(false);
      },
      'Team created. You are its first manager.',
      resource.reload,
    );
  };

  const listAccessChanged =
    resource.error !== null && isAccessError(resource.error.status, resource.error.code);

  return (
    <section className="h-full overflow-y-auto p-4 sm:p-6">
      <div className="mx-auto flex max-w-5xl flex-col gap-6 pb-8">
        <header className="flex flex-wrap items-end justify-between gap-4 border-b border-line/70 pb-6">
          <div>
            <p className="font-mono text-2xs uppercase tracking-[0.22em] text-ember">
              Shared workspaces
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">Teams</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
              Keep collaboration focused: shared research, a lightweight team board, and access
              controls in one workspace.
            </p>
          </div>
          {user.is_active && teams?.length !== 0 ? (
            <Button
              variant="secondary"
              onClick={() => setCreating((value) => !value)}
              aria-expanded={creating}
              aria-controls="create-team-panel"
            >
              {creating ? 'Close create form' : 'Create a team'}
            </Button>
          ) : null}
        </header>
        <TeamInvitationInbox onAccepted={resource.reload} />
        {action.error ? <Alert tone="error">{action.error}</Alert> : null}
        {action.notice ? (
          <p role="status" className="text-sm text-good">
            {action.notice}
          </p>
        ) : null}
        {resource.error ? (
          <Alert
            tone={listAccessChanged ? 'warning' : 'error'}
            title={listAccessChanged ? 'Team access changed' : undefined}
          >
            {listAccessChanged
              ? 'Your team access may have changed. Refresh the list to load your current workspaces.'
              : describeError(resource.error)}{' '}
            <Button
              variant="ghost"
              onClick={() => {
                void resource.reload();
              }}
            >
              Retry teams
            </Button>
          </Alert>
        ) : null}
        {resource.loading && teams === null ? (
          <LoadingNote label="Loading team workspaces" />
        ) : null}
        {teams?.length === 0 ? (
          <>
            <EmptyTeams onCreate={() => setCreating(true)} />
            {creating ? (
              <CreationPanel
                open
                busy={action.busy}
                onOpen={() => setCreating(false)}
                onSave={submitTeam}
              />
            ) : null}
          </>
        ) : null}
        {teams && teams.length > 0 ? (
          <>
            {creating ? (
              <CreationPanel
                open
                busy={action.busy}
                onOpen={() => setCreating(false)}
                onSave={submitTeam}
              />
            ) : null}
            <SelectField
              label="Team workspace"
              hint="Choose a workspace to open its dashboard."
              value={teamId ?? ''}
              options={teams.map((team) => ({
                value: team.id,
                label: `${team.name}${team.is_active ? '' : ' (archived)'}`,
              }))}
              onChange={(event) => {
                setSelected(event.target.value);
              }}
            />
            {teamId ? (
              <TeamPanel key={teamId} id={teamId} user={user} refreshList={resource.reload} />
            ) : null}
          </>
        ) : null}
      </div>
    </section>
  );
}

export default function TeamsPage() {
  const user = useAuthStore((state) => state.user);
  return user ? <TeamsWorkspace key={`${user.id}:${user.role}`} user={user} /> : null;
}
