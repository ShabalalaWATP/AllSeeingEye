import { useCallback, useEffect, useState } from 'react';

import { describeError } from '@/lib/api/errors';
import {
  acceptTeamInvitation,
  declineTeamInvitation,
  listMyTeamInvitations,
  type TeamInvitation,
} from '@/lib/api/teamInvitations';

export interface TeamInvitationInboxState {
  open: boolean;
  setOpen: (open: boolean) => void;
  /** Pending invitations, or null until the first load settles. */
  items: TeamInvitation[] | null;
  busy: boolean;
  error: string | null;
  notice: string | null;
  respond: (invitation: TeamInvitation, accept: boolean) => Promise<void>;
}

/**
 * Loads pending invitations on mount so the summary can show a count, and opens the
 * section once when the first load finds any. Later closes are the reader's choice.
 */
export function useTeamInvitationInbox(onAccepted: () => Promise<void>): TeamInvitationInboxState {
  const [open, setOpenState] = useState(false);
  const [items, setItems] = useState<TeamInvitation[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async (): Promise<TeamInvitation[] | null> => {
    try {
      const page = await listMyTeamInvitations();
      const pending = page.items.filter((item) => item.status === 'pending');
      setItems(pending);
      setError(null);
      return pending;
    } catch (reason) {
      setError(describeError(reason));
      return null;
    }
  }, []);

  useEffect(() => {
    let active = true;
    // State changes only after the request settles; the lint rule cannot see the await.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load().then((pending) => {
      if (active && pending !== null && pending.length > 0) setOpenState(true);
    });
    return () => {
      active = false;
    };
  }, [load]);

  const setOpen = (next: boolean) => {
    setOpenState(next);
    // A failed load is retried when the reader opens the section to see why.
    if (next && error !== null) void load();
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
      setItems((current) => (current ?? []).filter((item) => item.id !== invitation.id));
    } catch (reason) {
      // Reload first: a successful load clears the error, which would hide why this failed.
      await load();
      setError(describeError(reason));
    } finally {
      setBusy(false);
    }
  };

  return { open, setOpen, items, busy, error, notice, respond };
}
