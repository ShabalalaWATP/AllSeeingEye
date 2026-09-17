import { useState } from 'react';

import { AdminIcon } from '@/components/admin/AdminIcon';
import { ADMIN_CARD, EmptyState } from '@/components/admin/AdminPage';
import { Button } from '@/components/ui/Button';
import type { LlmProfile } from '@/lib/api/llm';
import type { User } from '@/lib/api/schemas';
import type { Team } from '@/lib/api/teams';

import { AiUsagePolicies } from './AiUsagePolicies';
import { LlmProfileRow } from './LlmProfileRow';
import { TEXT_ROLES } from './llmPresentation';

export function LlmDraftsSection({
  drafts,
  teams,
  users,
  encryption,
  applying,
  hasGlobal,
  onEdit,
  onDeleted,
  onTested,
  onApply,
}: {
  drafts: readonly LlmProfile[];
  teams: Team[];
  users: User[];
  encryption: boolean;
  applying: boolean;
  hasGlobal: boolean;
  onEdit: (profile: LlmProfile, models: readonly string[]) => void;
  onDeleted: (id: string) => void;
  onTested: (profile: LlmProfile) => void;
  onApply: (profile: LlmProfile, teamId: string | null, userId?: string) => void;
}) {
  return (
    <section aria-label="Saved connection drafts" className={`${ADMIN_CARD} space-y-3`}>
      <div>
        <h2 className="text-base font-semibold">Saved connections</h2>
        <p className="mt-1 text-sm text-muted">
          Keep additional models ready here. Test a connection, then assign it to the site, a team
          or a personal workspace.
        </p>
      </div>
      {drafts.length === 0 ? (
        <EmptyState icon="ai" title="No additional connections.">
          Add another model connection without replacing your default. Each connection keeps its own
          model, settings and credentials.
        </EmptyState>
      ) : (
        <ul>
          {drafts.map((profile) => (
            <LlmProfileRow
              key={`${profile.id}:${profile.revision}`}
              profile={profile}
              teams={teams}
              users={users}
              disabled={!encryption}
              applying={applying}
              hasGlobal={hasGlobal}
              legacyProtected={
                !hasGlobal &&
                profile.enabled &&
                profile.roles.some((role) => TEXT_ROLES.includes(role))
              }
              onEdit={onEdit}
              onDeleted={onDeleted}
              onTested={onTested}
              onApply={onApply}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

/** Allowance controls mount only on request, so their policy data loads on demand. */
export function AllowanceControls({
  users,
  teams,
}: {
  users: readonly User[];
  teams: readonly Team[];
}) {
  const [open, setOpen] = useState(false);
  if (open)
    return (
      <div className={`${ADMIN_CARD} space-y-4`}>
        <Button variant="ghost" onClick={() => setOpen(false)}>
          Close allowance controls
        </Button>
        <AiUsagePolicies users={users} teams={teams} />
      </div>
    );
  return (
    <div className={`${ADMIN_CARD} flex flex-wrap items-center justify-between gap-4`}>
      <div className="flex min-w-0 items-start gap-3">
        <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg border border-line/80 bg-surface-2 text-ember">
          <AdminIcon name="gauge" size={16} />
        </span>
        <div className="min-w-0">
          <h2 className="text-base font-semibold">AI access and usage</h2>
          <p className="mt-1 text-sm text-muted">
            Set bounded daily, weekly or monthly request and token allowances for the site,
            individual users or teams.
          </p>
        </div>
      </div>
      <Button variant="secondary" onClick={() => setOpen(true)}>
        Open allowance controls
      </Button>
    </div>
  );
}
