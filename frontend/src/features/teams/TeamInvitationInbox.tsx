import { useState } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import {
  acceptTeamInvitation,
  declineTeamInvitation,
  listMyTeamInvitations,
  type TeamInvitation,
} from '@/lib/api/teamInvitations';

function dateLabel(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? 'date unavailable' : date.toLocaleDateString();
}

export function TeamInvitationInbox({ onAccepted }: { onAccepted: () => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<TeamInvitation[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = async () => {
    setError(null);
    try {
      const page = await listMyTeamInvitations();
      setItems(page.items.filter((item) => item.status === 'pending'));
    } catch (reason) {
      setError(describeError(reason));
    }
  };

  const respond = async (invitation: TeamInvitation, accept: boolean) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      if (accept) {
        await acceptTeamInvitation(invitation.id, invitation.revision);
        await onAccepted();
        setNotice('Invitation accepted. The team is now available in your workspaces.');
      } else {
        await declineTeamInvitation(invitation.id, invitation.revision);
        setNotice('Invitation declined.');
      }
      setItems((current) => current.filter((item) => item.id !== invitation.id));
    } catch (reason) {
      setError(describeError(reason));
      await load();
    } finally {
      setBusy(false);
    }
  };

  return (
    <details
      className="border border-line/70 bg-surface/40 px-5 py-4"
      onToggle={(event) => {
        const nextOpen = event.currentTarget.open;
        setOpen(nextOpen);
        if (nextOpen) void load();
      }}
    >
      <summary className="cursor-pointer text-sm font-semibold">
        Team invitations{' '}
        <span className="text-xs font-normal text-muted">Review access requests</span>
      </summary>
      {open ? (
        <div className="mt-4 flex flex-col gap-3">
          {error ? <Alert tone="error">{error}</Alert> : null}
          {notice ? (
            <p role="status" className="text-sm text-good">
              {notice}
            </p>
          ) : null}
          {items.length === 0 && !error ? (
            <p className="text-sm text-muted">No pending team invitations.</p>
          ) : (
            <ul className="divide-y divide-line/70 border-y border-line/70">
              {items.map((invitation) => (
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
