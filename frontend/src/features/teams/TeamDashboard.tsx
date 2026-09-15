import { useState } from 'react';
import type { ReactNode } from 'react';

import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import { getTeamAiUsage, type AiUsageSummary } from '@/lib/api/aiUsage';
import type { User } from '@/lib/api/schemas';
import type { TeamDetail } from '@/lib/api/teams';

import { TeamBoard } from './TeamBoard';
import type { TeamCapabilities } from './teamCapabilities';

export type TeamDashboardTab = 'overview' | 'research' | 'board' | 'members';

const TABS: readonly { id: TeamDashboardTab; label: string; detail: string }[] = [
  { id: 'overview', label: 'Overview', detail: 'Team pulse and quick actions' },
  { id: 'research', label: 'Research', detail: 'Shared analysis workspace' },
  { id: 'board', label: 'Board', detail: 'Short team updates' },
  { id: 'members', label: 'Members', detail: 'People and access' },
];
const DEFAULT_TAB: (typeof TABS)[number] = {
  id: 'overview',
  label: 'Overview',
  detail: 'Team pulse and quick actions',
};

function StatusPill({ active }: { active: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${
        active ? 'border-good/40 bg-good/10 text-good' : 'border-line bg-surface-2 text-muted'
      }`}
    >
      <span
        aria-hidden="true"
        className={`size-1.5 rounded-full ${active ? 'bg-good' : 'bg-muted'}`}
      />
      {active ? 'Active workspace' : 'Archived workspace'}
    </span>
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

function TeamAllowance({ teamId }: { teamId: string }) {
  const [items, setItems] = useState<AiUsageSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await getTeamAiUsage(teamId));
    } catch (reason) {
      setError(describeError(reason));
    } finally {
      setLoading(false);
    }
  };
  const rows = items ?? [];

  return (
    <details
      className="border border-line/70 bg-surface/40 p-5"
      onToggle={(event) => {
        if (event.currentTarget.open && items === null && !loading) void load();
      }}
    >
      <summary className="cursor-pointer text-sm font-semibold">AI allowance</summary>
      <div className="mt-4">
        {loading ? <p className="text-sm text-muted">Loading allowance…</p> : null}
        {error ? <p className="text-sm text-critical">{error}</p> : null}
        {items !== null && rows.length === 0 ? (
          <p className="text-sm text-muted">No allowance policy is active for this workspace.</p>
        ) : null}
        {rows.length > 0 ? (
          <ul className="grid gap-3 sm:grid-cols-2">
            {rows.map((item) => {
              const requestLimit = item.policy.request_limit;
              const tokenLimit = item.policy.token_limit;
              return (
                <li key={item.policy.id} className="border border-line/70 p-3 text-sm">
                  <p className="font-medium capitalize">
                    {item.policy.scope} · {item.policy.period}
                  </p>
                  <p className="mt-1 text-muted">
                    Requests: {item.used_requests}
                    {requestLimit === null ? ' / unlimited' : ` / ${requestLimit}`}
                  </p>
                  <p className="text-muted">
                    Tokens: {item.used_tokens.toLocaleString()}
                    {tokenLimit === null ? ' / unlimited' : ` / ${tokenLimit.toLocaleString()}`}
                  </p>
                </li>
              );
            })}
          </ul>
        ) : null}
      </div>
    </details>
  );
}

function Overview({
  detail,
  capabilities,
  teamId,
  onTabChange,
}: {
  detail: TeamDetail;
  capabilities: TeamCapabilities;
  teamId: string;
  onTabChange: (tab: TeamDashboardTab) => void;
}) {
  const memberCount = detail.members.length;
  const activeMembers = detail.members.filter((member) => member.is_active).length;
  const managers = detail.members.filter(
    (member) => member.is_active && member.role === 'manager',
  ).length;
  const created = detail.team.created_at.slice(0, 10);

  return (
    <div className="flex flex-col gap-7" aria-labelledby="team-overview-heading">
      <div>
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-ember">
          Workspace pulse
        </p>
        <h3 id="team-overview-heading" className="mt-2 text-xl font-semibold">
          A calm view of who can work here
        </h3>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Keep the team small and purposeful. Use Members to manage access, Research to create
          shared analysis, and Board for short operational notes.
        </p>
      </div>
      <div className="grid gap-6 border-y border-line/70 py-6 sm:grid-cols-3">
        <Stat label="People" value={String(memberCount)} detail={`${activeMembers} active`} />
        <Stat label="Managers" value={String(managers)} detail="Team-level managers" />
        <Stat label="Created" value={created} detail="Workspace start date" />
      </div>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.3fr)_minmax(260px,0.7fr)]">
        <section
          className="rounded-card border border-line bg-surface/60 p-5"
          aria-labelledby="team-next-heading"
        >
          <h4 id="team-next-heading" className="text-sm font-semibold">
            Next actions
          </h4>
          <ul className="mt-4 space-y-3 text-sm text-muted">
            <li className="flex gap-3">
              <span aria-hidden="true" className="mt-2 size-1.5 shrink-0 rounded-full bg-ember" />
              <span>
                {memberCount === 0
                  ? 'Add the first colleague from Members.'
                  : `${activeMembers} active ${activeMembers === 1 ? 'person is' : 'people are'} available to collaborate.`}
              </span>
            </li>
            <li className="flex gap-3">
              <span aria-hidden="true" className="mt-2 size-1.5 shrink-0 rounded-full bg-cyan" />
              <span>Start a research task and save the finished report into this workspace.</span>
            </li>
            <li className="flex gap-3">
              <span aria-hidden="true" className="mt-2 size-1.5 shrink-0 rounded-full bg-amber" />
              <span>Use the Board for short handovers, questions, and context between runs.</span>
            </li>
          </ul>
        </section>
        <section className="border border-line/70 p-5" aria-labelledby="team-access-heading">
          <h4 id="team-access-heading" className="text-sm font-semibold">
            Your access
          </h4>
          <p className="mt-2 text-sm leading-6 text-muted">
            {capabilities.isAdmin
              ? 'Administrator access applies across this workspace.'
              : capabilities.isManager
                ? 'You are a team manager and can maintain ordinary member access.'
                : capabilities.isMember
                  ? 'You can use shared team workspaces and view the roster.'
                  : 'Your membership is currently read-only.'}
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => onTabChange('members')}>
              Open members
            </Button>
            {capabilities.canManageMembers ? (
              <Button variant="ghost" onClick={() => onTabChange('members')}>
                Manage access
              </Button>
            ) : null}
          </div>
        </section>
      </div>
      <TeamAllowance teamId={teamId} />
    </div>
  );
}

function ResearchWorkspace({ teamId }: { teamId: string }) {
  return (
    <section className="flex flex-col gap-6" aria-labelledby="team-research-heading">
      <div>
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-cyan">
          Shared analysis
        </p>
        <h3 id="team-research-heading" className="mt-2 text-xl font-semibold">
          Research for this team
        </h3>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Start work from the research workspace, then choose this team in the workspace selector to
          make the run and its final report available to your colleagues.
        </p>
      </div>
      <div className="grid gap-4 border-y border-line/70 py-5 sm:grid-cols-2">
        <a
          href={`/research?team_id=${encodeURIComponent(teamId)}`}
          className="group border border-line bg-surface/60 p-5 transition-colors hover:border-cyan/60 hover:bg-surface"
        >
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-cyan">
            Create
          </span>
          <h4 className="mt-2 text-base font-semibold group-hover:text-cyan">
            Start team research
          </h4>
          <p className="mt-2 text-sm leading-6 text-muted">
            Set a question, collect evidence, and publish a report to the team.
          </p>
        </a>
        <a
          href={`/reports?team_id=${encodeURIComponent(teamId)}`}
          className="group border border-line bg-surface/60 p-5 transition-colors hover:border-ember/60 hover:bg-surface"
        >
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ember">
            Review
          </span>
          <h4 className="mt-2 text-base font-semibold group-hover:text-ember">
            Open saved reports
          </h4>
          <p className="mt-2 text-sm leading-6 text-muted">
            Review the team’s shared evidence and finished reporting.
          </p>
        </a>
      </div>
      <p className="text-xs text-muted">
        Team visibility is checked again when a report is opened, edited, or exported.
      </p>
    </section>
  );
}

export function TeamDashboard({
  detail,
  user,
  capabilities,
  activeTab,
  onTabChange,
  actions,
  members,
}: {
  detail: TeamDetail;
  user: User;
  capabilities: TeamCapabilities;
  activeTab: TeamDashboardTab;
  onTabChange: (tab: TeamDashboardTab) => void;
  actions?: ReactNode;
  members: ReactNode;
}) {
  const selectedTab = TABS.find((tab) => tab.id === activeTab) ?? DEFAULT_TAB;
  return (
    <div className="flex min-w-0 flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-line/70 pb-6">
        <div className="min-w-0">
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-ember">
            Team workspace
          </p>
          <h2 className="mt-2 break-words text-2xl font-semibold tracking-tight">
            {detail.team.name}
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
            {detail.team.description ??
              'Shared research, short team context, and access managed in one place.'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <StatusPill active={detail.team.is_active} />
          {actions}
        </div>
      </header>
      <nav
        aria-label="Team workspace sections"
        className="-mb-px flex gap-1 overflow-x-auto border-b border-line/70"
      >
        {TABS.map((tab) => {
          const selected = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              id={`team-${tab.id}-tab`}
              type="button"
              role="tab"
              aria-selected={selected}
              aria-controls={`team-panel-${tab.id}`}
              onClick={() => onTabChange(tab.id)}
              className={`min-h-12 shrink-0 border-b-2 px-3 text-left text-sm transition-colors ${
                selected
                  ? 'border-ember text-text'
                  : 'border-transparent text-muted hover:border-line hover:text-text'
              }`}
            >
              <span className="block font-medium">{tab.label}</span>
              <span className="mt-0.5 hidden text-[11px] text-muted lg:block">{tab.detail}</span>
            </button>
          );
        })}
      </nav>
      <div
        id={`team-panel-${selectedTab.id}`}
        role="tabpanel"
        aria-labelledby={`team-${selectedTab.id}-tab`}
        className="min-w-0 pb-8"
      >
        {activeTab === 'overview' ? (
          <Overview
            detail={detail}
            capabilities={capabilities}
            teamId={detail.team.id}
            onTabChange={onTabChange}
          />
        ) : null}
        {activeTab === 'research' ? <ResearchWorkspace teamId={detail.team.id} /> : null}
        {activeTab === 'board' ? (
          <TeamBoard
            teamId={detail.team.id}
            teamName={detail.team.name}
            userId={user.id}
            capabilities={capabilities}
          />
        ) : null}
        {activeTab === 'members' ? members : null}
      </div>
      <p className="sr-only">Signed in as {user.display_name}</p>
    </div>
  );
}
