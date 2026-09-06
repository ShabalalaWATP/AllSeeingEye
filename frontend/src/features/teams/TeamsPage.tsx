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
import { useTeamAction, useTeamsResource } from './useTeams';

function TeamsWorkspace({ user }: { user: User }) {
  const resource = useTeamsResource(listTeams);
  const action = useTeamAction();
  const [selected, setSelected] = useState('');
  const teams = resource.data;
  const teamId = teams?.find((team) => team.id === selected)?.id ?? teams?.[0]?.id;
  return (
    <section className="h-full overflow-y-auto p-4 sm:p-6">
      <div className="mx-auto flex max-w-4xl flex-col gap-6">
        <header>
          <p className="text-xs font-medium uppercase tracking-widest text-ember">
            People and access
          </p>
          <h1 className="mt-2 text-2xl font-semibold">Teams</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted">
            View team rosters and maintain memberships. Account roles and security settings are
            managed separately by administrators.
          </p>
        </header>
        {action.error ? <Alert tone="error">{action.error}</Alert> : null}
        {action.notice ? (
          <p role="status" className="text-sm text-muted">
            {action.notice}
          </p>
        ) : null}
        {user.role === 'admin' ? (
          <details className="rounded-card border border-line bg-surface p-4">
            <summary className="cursor-pointer text-sm font-medium">Create a team</summary>
            <div className="mt-4">
              <TeamNameForm
                busy={action.busy}
                onSave={(name) => {
                  void action.run(
                    async () => {
                      const team = await createTeam(name);
                      setSelected(team.id);
                    },
                    'Team created.',
                    resource.reload,
                  );
                }}
              />
            </div>
          </details>
        ) : null}
        {resource.error ? (
          <Alert tone="error">
            {describeError(resource.error)}{' '}
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
        {resource.loading ? <LoadingNote label="Loading teams" /> : null}
        {teams?.length === 0 ? (
          <p className="rounded-card border border-line p-5 text-sm text-muted">
            {user.role === 'admin'
              ? 'No teams yet. Create a team to assign its members.'
              : 'You are not assigned to a team. Contact an administrator to arrange membership.'}
          </p>
        ) : null}
        {teams && teamId ? (
          <>
            <SelectField
              label="Team roster"
              value={teamId}
              options={teams.map((team) => ({
                value: team.id,
                label: `${team.name}${team.is_active ? '' : ' (archived)'}`,
              }))}
              onChange={(event) => {
                setSelected(event.target.value);
              }}
            />
            <TeamPanel key={teamId} id={teamId} user={user} refreshList={resource.reload} />
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
