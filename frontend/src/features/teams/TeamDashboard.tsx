import type { ReactNode } from 'react';

import type { User } from '@/lib/api/schemas';
import type { TeamDetail } from '@/lib/api/teams';

import { TeamBoard } from './TeamBoard';
import { TeamOverview } from './TeamOverview';
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

function ResearchWorkspace({ teamId }: { teamId: string }) {
  return (
    <section className="flex flex-col gap-6" aria-labelledby="team-research-heading">
      <div>
        <p className="font-mono text-2xs uppercase tracking-[0.22em] text-cyan">Shared analysis</p>
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
          <span className="font-mono text-2xs uppercase tracking-[0.18em] text-cyan">Create</span>
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
          <span className="font-mono text-2xs uppercase tracking-[0.18em] text-ember">Review</span>
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
          <p className="font-mono text-2xs uppercase tracking-[0.22em] text-ember">
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
          <TeamOverview
            teamId={detail.team.id}
            capabilities={capabilities}
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
