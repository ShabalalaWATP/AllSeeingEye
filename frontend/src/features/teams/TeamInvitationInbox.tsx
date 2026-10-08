import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';

import { useTeamInvitationInbox } from './useTeamInvitationInbox';

function dateLabel(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? 'date unavailable' : date.toLocaleDateString();
}

/** Short summary text, so pending invitations are visible without opening the section. */
export function invitationSummary(items: readonly unknown[] | null, error: string | null): string {
  if (items === null) return error === null ? 'Checking for invitations' : 'Could not check';
  if (items.length === 0) return 'None pending';
  return `${items.length} pending`;
}

export function TeamInvitationInbox({ onAccepted }: { onAccepted: () => Promise<void> }) {
  const { open, setOpen, items, busy, error, notice, respond } = useTeamInvitationInbox(onAccepted);
  const pending = items ?? [];

  return (
    <details
      className="border border-line/70 bg-surface/40 px-5 py-4"
      open={open}
      onToggle={(event) => {
        const nextOpen = event.currentTarget.open;
        if (nextOpen !== open) setOpen(nextOpen);
      }}
    >
      <summary className="cursor-pointer text-sm font-semibold">
        Team invitations{' '}
        <span className="text-xs font-normal text-muted">{invitationSummary(items, error)}</span>
      </summary>
      {open ? (
        <div className="mt-4 flex flex-col gap-3">
          {error ? <Alert tone="error">{error}</Alert> : null}
          {notice ? (
            <p role="status" className="text-sm text-good">
              {notice}
            </p>
          ) : null}
          {items === null && error === null ? (
            <p className="text-sm text-muted">Checking for team invitations.</p>
          ) : pending.length === 0 && !error ? (
            <p className="text-sm text-muted">No pending team invitations.</p>
          ) : (
            <ul className="divide-y divide-line/70 border-y border-line/70">
              {pending.map((invitation) => (
                <li
                  key={invitation.id}
                  className="flex flex-wrap items-start justify-between gap-4 py-4"
                >
                  <div>
                    <p className="font-medium">{invitation.team_name ?? 'Team workspace'}</p>
                    <p className="mt-1 text-sm text-muted">
                      Invited by {invitation.inviter_display_name ?? 'a team manager'} · expires{' '}
                      {dateLabel(invitation.expires_at)}
                    </p>
                    {invitation.note ? <p className="mt-2 text-sm">{invitation.note}</p> : null}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      busy={busy}
                      onClick={() => void respond(invitation, true)}
                    >
                      Accept
                    </Button>
                    <Button
                      variant="ghost"
                      busy={busy}
                      onClick={() => void respond(invitation, false)}
                    >
                      Decline
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </details>
  );
}
