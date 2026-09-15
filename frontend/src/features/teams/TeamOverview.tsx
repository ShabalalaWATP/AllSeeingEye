import type { ReactNode } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import type { TeamDashboard, TeamDashboardAction } from '@/lib/api/teamBoard';

import { TeamAllowance } from './TeamAllowance';
import type { TeamDashboardTab } from './TeamDashboard';
import type { TeamCapabilities } from './teamCapabilities';
import { useTeamDashboard } from './useTeamDashboard';

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value),
  );
}

function Stat({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="border-l-2 border-ember/60 pl-4">
      <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-text">{value}</p>
      <p className="mt-1 text-xs text-muted">{detail}</p>
    </div>
  );
}

function Panel({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section className="border border-line/70 bg-surface/40 p-5" aria-labelledby={id}>
      <h4 id={id} className="text-sm font-semibold">
        {title}
      </h4>
      <div className="mt-3 text-sm">{children}</div>
    </section>
  );
}

function actionText(item: TeamDashboardAction): string {
  if (item.kind === 'owner_not_member') {
    return 'Its owner is no longer an active member, so scheduled runs stop. A manager can create a reviewed replacement.';
  }
  return item.kind === 'edition_blocked'
    ? `A run was blocked on ${formatDate(item.occurred_at)}.`
    : `A run failed on ${formatDate(item.occurred_at)}.`;
}

function roleText(data: TeamDashboard, capabilities: TeamCapabilities): string {
  if (data.team.role === 'manager') return 'Manager';
  if (data.team.role === 'member') return 'Member';
  return capabilities.isAdmin ? 'Administrator' : 'No membership';
}

function DashboardBody({
  data,
  capabilities,
  onTabChange,
}: {
  data: TeamDashboard;
  capabilities: TeamCapabilities;
  onTabChange: (tab: TeamDashboardTab) => void;
}) {
  const unread = data.unread_count >= 100 ? '100+' : String(data.unread_count);
  return (
    <>
      <div className="grid gap-6 border-y border-line/70 py-6 sm:grid-cols-3">
        <Stat label="People" value={String(data.team.member_count)} detail="Current members" />
        <Stat label="Your role" value={roleText(data, capabilities)} detail="In this team" />
        <Stat label="Board" value={unread} detail="Unread posts" />
      </div>
      {data.pinned.length > 0 ? (
        <Panel id="team-pinned-heading" title="Pinned announcements">
          <ul className="space-y-3">
            {data.pinned.map((post) => (
              <li key={post.id} className="border-l-2 border-amber/60 pl-3">
                <p className="whitespace-pre-wrap break-words leading-6 text-text">{post.text}</p>
                <p className="mt-1 text-xs text-muted">
                  {post.author_name} · {formatDate(post.created_at)}
                </p>
              </li>
            ))}
          </ul>
        </Panel>
      ) : null}
      {data.action_items.length > 0 ? (
        <Panel id="team-actions-heading" title="Action needed">
          <ul className="space-y-3">
            {data.action_items.map((item) => (
              <li key={`${item.kind}-${item.edition_id ?? item.schedule_id}`}>
                <a className="font-medium text-text hover:underline" href="/subscriptions">
                  {item.schedule_name}
                </a>
                <p className="mt-1 text-muted">{actionText(item)}</p>
              </li>
            ))}
          </ul>
        </Panel>
      ) : null}
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel id="team-reports-heading" title="Recent shared reports">
          {data.recent_reports.length === 0 ? (
            <p className="text-muted">No reports have been shared with this team yet.</p>
          ) : (
            <ul className="space-y-3">
              {data.recent_reports.map((report) => (
                <li key={report.id}>
                  <a
                    className="font-medium text-text hover:underline"
                    href={`/reports/${encodeURIComponent(report.id)}?version=${report.latest_version}`}
                  >
                    {report.title}
                  </a>
                  <p className="mt-1 text-xs text-muted">
                    Version {report.latest_version} · {formatDate(report.created_at)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Panel>
        <Panel id="team-runs-heading" title="Next subscription runs">
          {data.upcoming_runs.length === 0 ? (
            <p className="text-muted">No team subscriptions are scheduled.</p>
          ) : (
            <ul className="space-y-3">
              {data.upcoming_runs.map((run) => (
                <li key={run.schedule_id}>
                  <a className="font-medium text-text hover:underline" href="/subscriptions">
                    {run.name}
                  </a>
                  <p className="mt-1 text-xs text-muted">
                    <span className="capitalize">{run.cadence}</span> ·{' '}
                    {formatDate(run.next_run_at)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={() => onTabChange('board')}>
          Open board
        </Button>
        <Button variant="ghost" onClick={() => onTabChange('members')}>
          {capabilities.canManageMembers ? 'Manage access' : 'Open members'}
        </Button>
      </div>
    </>
  );
}

export function TeamOverview({
  teamId,
  capabilities,
  onTabChange,
}: {
  teamId: string;
  capabilities: TeamCapabilities;
  onTabChange: (tab: TeamDashboardTab) => void;
}) {
  const { data, error, loading, reload } = useTeamDashboard(teamId);
  return (
    <div className="flex flex-col gap-7" aria-labelledby="team-overview-heading">
      <div>
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-ember">
          Workspace pulse
        </p>
        <h3 id="team-overview-heading" className="mt-2 text-xl font-semibold">
          What needs attention in this team
        </h3>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Pinned notes, recently shared reports and upcoming subscription runs. Access is checked
          again whenever you open an item.
        </p>
      </div>
      {loading && data === null ? <LoadingNote label="Loading team overview" /> : null}
      {error ? (
        <Alert tone="error">
          {error}{' '}
          <Button variant="ghost" onClick={() => void reload()}>
            Retry
          </Button>
        </Alert>
      ) : null}
      {data ? (
        <DashboardBody data={data} capabilities={capabilities} onTabChange={onTabChange} />
      ) : null}
      <TeamAllowance teamId={teamId} />
    </div>
  );
}
