import { useCallback } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import type { User } from '@/lib/api/schemas';
import { getTeam, removeMember, setMember, updateTeam } from '@/lib/api/teams';

import { AddMemberForm, TeamNameForm } from './TeamForms';
import { ConfirmAction, TeamRoster } from './TeamRoster';
import { useTeamAction, useTeamsResource } from './useTeams';

export function TeamPanel({
  id,
  user,
  refreshList,
}: {
  id: string;
  user: User;
  refreshList: () => Promise<void>;
}) {
  const load = useCallback(() => getTeam(id), [id]);
  const resource = useTeamsResource(load);
  const action = useTeamAction();
  const detail = resource.data;
  const admin = user.role === 'admin';
  const canManage =
    detail !== null &&
    detail.team.is_active &&
    (admin ||
      (user.role === 'manager' &&
        detail.members.some((member) => member.user_id === user.id && member.role === 'manager')));
  const reload = resource.reload;
  return (
    <section className="flex min-w-0 flex-col gap-5" aria-label="Selected team">
      {action.error ? <Alert tone="error">{action.error}</Alert> : null}
      {action.notice ? (
        <p role="status" className="text-sm text-muted">
          {action.notice}
        </p>
      ) : null}
      {resource.error ? (
        <Alert tone="error">
          {describeError(resource.error)}{' '}
          <Button
            variant="ghost"
            onClick={() => {
              void reload();
            }}
          >
            Retry roster
          </Button>
        </Alert>
      ) : null}
      {resource.loading ? <LoadingNote label="Loading team roster" /> : null}
      {detail ? (
        <>
          <header className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="break-words text-xl font-semibold">{detail.team.name}</h2>
              <p className="mt-1 text-sm text-muted">
                {detail.members.length} members · {detail.team.is_active ? 'Active' : 'Archived'}
              </p>
            </div>
            <Button
              variant="ghost"
              disabled={action.busy}
              onClick={() => {
                void reload();
              }}
            >
              Refresh roster
            </Button>
          </header>
          {!detail.team.is_active ? (
            <p className="text-sm text-muted">
              This team is archived. Its roster is read-only until an administrator reactivates it.
            </p>
          ) : null}
          {!admin && !canManage ? (
            <p className="text-sm text-muted">
              You can view this roster. Membership changes require a designated team manager or
              administrator.
            </p>
          ) : null}
          {!admin && canManage ? (
            <p className="text-sm text-muted">
              You manage ordinary members of this team. Administrators assign team managers.
            </p>
          ) : null}
          <TeamRoster
            members={detail.members}
            admin={admin}
            canManage={canManage}
            busy={action.busy}
            onRemove={(member) => {
              void action.run(() => removeMember(id, member.user_id), 'Member removed.', reload);
            }}
            onRole={(member, role) => {
              void action.run(
                () => setMember(id, { email: member.email, role }),
                'Team role updated.',
                reload,
              );
            }}
          />
          {canManage ? (
            <AddMemberForm
              admin={admin}
              busy={action.busy}
              onSave={(input) => {
                void action.run(() => setMember(id, input), 'Membership saved.', reload);
              }}
            />
          ) : null}
          {admin ? (
            <details className="border-t border-line pt-4">
              <summary className="cursor-pointer text-sm font-medium">Team settings</summary>
              <div className="mt-4 flex flex-col gap-4">
                <TeamNameForm
                  key={detail.team.name}
                  name={detail.team.name}
                  busy={action.busy}
                  onSave={(name) => {
                    void action.run(
                      () => updateTeam(id, { name }),
                      'Team renamed.',
                      async () => {
                        await reload();
                        await refreshList();
                      },
                    );
                  }}
                />
                {detail.team.is_active ? (
                  <ConfirmAction
                    label="Archive team"
                    question="Archive this team and make its roster read-only?"
                    busy={action.busy}
                    onConfirm={() => {
                      void action.run(
                        () => updateTeam(id, { is_active: false }),
                        'Team archived.',
                        async () => {
                          await reload();
                          await refreshList();
                        },
                      );
                    }}
                  />
                ) : (
                  <Button
                    variant="secondary"
                    busy={action.busy}
                    onClick={() => {
                      void action.run(
                        () => updateTeam(id, { is_active: true }),
                        'Team reactivated.',
                        async () => {
                          await reload();
                          await refreshList();
                        },
                      );
                    }}
                  >
                    Reactivate team
                  </Button>
                )}
              </div>
            </details>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
