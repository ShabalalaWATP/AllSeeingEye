import { useCallback, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import type { User } from '@/lib/api/schemas';
import {
  changeMemberRole,
  getTeam,
  leaveTeam,
  removeMember,
  setMember,
  updateTeam,
} from '@/lib/api/teams';

import { AddMemberForm, TeamNameForm } from './TeamForms';
import { ConfirmAction, TeamRoster } from './TeamRoster';
import { TeamDashboard, type TeamDashboardTab } from './TeamDashboard';
import { TeamInvitationPanel } from './TeamInvitationPanel';
import { TeamReactivation } from './TeamReactivation';
import { teamCapabilities } from './teamCapabilities';
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
  const capabilities = teamCapabilities(user, detail);
  const admin = capabilities.isAdmin;
  const canManage = capabilities.canManageMembers;
  const canManageTeam = capabilities.canManageTeam;
  // Keep the roster as the landing view so existing team workflows remain one
  // click from the team selector. Overview, Research, and Board are available
  // alongside it in the dashboard tabs.
  const [activeTab, setActiveTab] = useState<TeamDashboardTab>('members');
  const reload = resource.reload;
  const accessRevoked =
    resource.error?.status === 401 ||
    resource.error?.status === 403 ||
    ['forbidden', 'membership_required', 'team_access_revoked'].includes(
      resource.error?.code ?? '',
    );
  return (
    <section className="flex min-w-0 flex-col gap-5" aria-label="Selected team">
      {action.error ? <Alert tone="error">{action.error}</Alert> : null}
      {action.notice ? (
        <p role="status" className="text-sm text-muted">
          {action.notice}
        </p>
      ) : null}
      {resource.error ? (
        <Alert
          tone={accessRevoked ? 'warning' : 'error'}
          title={accessRevoked ? 'Team access changed' : undefined}
        >
          {accessRevoked
            ? 'Your access to this team may have changed. Refresh the team list to check your current workspaces.'
            : describeError(resource.error)}{' '}
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
        <TeamDashboard
          detail={detail}
          user={user}
          capabilities={capabilities}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          actions={
            <Button
              variant="ghost"
              disabled={action.busy}
              onClick={() => {
                void reload();
              }}
            >
              Refresh roster
            </Button>
          }
          members={
            <div className="flex flex-col gap-6" aria-labelledby="team-members-heading">
              <div>
                <p className="font-mono text-2xs uppercase tracking-[0.22em] text-ember">
                  People and access
                </p>
                <h3 id="team-members-heading" className="mt-2 text-xl font-semibold">
                  Members
                </h3>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
                  {detail.members.length} people are listed in this workspace. Membership changes
                  are recorded and checked again by the server.
                </p>
              </div>
              {!detail.team.is_active ? (
                <Alert tone="warning">
                  This team is archived. Its roster is read-only until an administrator reactivates
                  it.
                </Alert>
              ) : null}
              {!admin && !canManage ? (
                <p className="text-sm text-muted">
                  You can view this roster. Membership changes require a designated team manager or
                  administrator.
                </p>
              ) : null}
              {!admin && canManage ? (
                <p className="text-sm text-muted">
                  You manage members. Invite people from the directory, then promote members to team
                  manager when needed.
                </p>
              ) : null}
              <TeamRoster
                members={detail.members}
                actor={user}
                team={detail.team}
                canManage={canManage}
                busy={action.busy}
                onRemove={(member) => {
                  void action.run(
                    () => removeMember(id, member.user_id),
                    'Member removed.',
                    reload,
                  );
                }}
                onRole={(member, role) => {
                  void action.run(
                    () => changeMemberRole(id, member.user_id, role),
                    'Team role updated.',
                    reload,
                  );
                }}
              />
              <TeamInvitationPanel teamId={id} canManage={canManage} />
              {admin && detail.team.is_active ? (
                <AddMemberForm
                  admin={admin}
                  allowManagerRole
                  busy={action.busy}
                  onSave={(input) => {
                    void action.run(() => setMember(id, input), 'Membership saved.', reload);
                  }}
                />
              ) : null}
              {capabilities.canLeave ? (
                <div className="border-t border-line pt-4">
                  <ConfirmAction
                    label="Leave team"
                    question="Leave this team? You will lose access to its research and board."
                    busy={action.busy}
                    onConfirm={() => {
                      void action.run(() => leaveTeam(id), 'You left the team.', refreshList);
                    }}
                  />
                  {capabilities.isManager ? (
                    <p className="mt-2 text-xs text-muted">
                      Appoint another manager first. The last active manager cannot leave.
                    </p>
                  ) : null}
                </div>
              ) : null}
              {canManageTeam ? (
                <details className="border-t border-line pt-4">
                  <summary className="cursor-pointer text-sm font-medium">Team settings</summary>
                  <div className="mt-4 flex flex-col gap-4">
                    <TeamNameForm
                      key={`${detail.team.name}:${detail.team.description ?? ''}`}
                      name={detail.team.name}
                      description={detail.team.description}
                      busy={action.busy}
                      onSave={(name, description) => {
                        const body =
                          description === undefined && detail.team.description === null
                            ? { name }
                            : { name, description: description?.trim() ?? null };
                        void action.run(
                          () => updateTeam(id, body),
                          'Team details saved.',
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
                    ) : admin ? (
                      <TeamReactivation
                        detail={detail}
                        actorId={user.id}
                        busy={action.busy}
                        onReactivate={(body) => {
                          void action.run(
                            () => updateTeam(id, body),
                            'Team reactivated.',
                            async () => {
                              await reload();
                              await refreshList();
                            },
                          );
                        }}
                      />
                    ) : null}
                    {!admin && !detail.team.is_active ? (
                      <p className="text-sm text-muted">
                        Only a site administrator can reactivate an archived team.
                      </p>
                    ) : null}
                  </div>
                </details>
              ) : null}
            </div>
          }
        />
      ) : null}
    </section>
  );
}
