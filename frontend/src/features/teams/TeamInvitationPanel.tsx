import { useState } from 'react';

import { DirectoryAvatar } from '@/components/account/DirectoryAvatar';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextAreaField, TextField } from '@/components/ui/Field';
import { describeError } from '@/lib/api/errors';
import { searchDirectory } from '@/lib/api/directoryProfile';
import {
  listTeamInvitations,
  sendTeamInvitation,
  withdrawTeamInvitation,
  type TeamInvitation,
} from '@/lib/api/teamInvitations';

function expiryLabel(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? 'expiry unavailable'
    : `expires ${date.toLocaleDateString()}`;
}

export function TeamInvitationPanel({ teamId, canManage }: { teamId: string; canManage: boolean }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [note, setNote] = useState('');
  const [results, setResults] = useState<Awaited<ReturnType<typeof searchDirectory>> | null>(null);
  const [pending, setPending] = useState<TeamInvitation[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  if (!canManage) return null;

  const loadPending = async () => {
    try {
      const page = await listTeamInvitations(teamId);
      setPending(page.items.filter((item) => item.status === 'pending'));
    } catch (reason) {
      setError(describeError(reason));
    }
  };

  const search = async () => {
    const value = query.trim();
    if (value.length < 2) {
      setError('Enter at least two characters to search the operator directory.');
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      setResults(await searchDirectory(value));
    } catch (reason) {
      setResults(null);
      setError(describeError(reason));
    } finally {
      setBusy(false);
    }
  };

  const invite = async (recipientId: string) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await sendTeamInvitation(teamId, recipientId, note);
      setNotice('Invitation sent. The account will appear in the team after acceptance.');
      setNote('');
      await loadPending();
    } catch (reason) {
      setError(describeError(reason));
    } finally {
      setBusy(false);
    }
  };

  const withdraw = async (invitation: TeamInvitation) => {
    setBusy(true);
    setError(null);
    try {
      await withdrawTeamInvitation(teamId, invitation.id, invitation.revision);
      setPending((items) => items.filter((item) => item.id !== invitation.id));
      setNotice('Invitation withdrawn.');
    } catch (reason) {
      setError(describeError(reason));
    } finally {
      setBusy(false);
    }
  };

  return (
    <details
      className="border-t border-line pt-4"
      onToggle={(event) => {
        const nextOpen = event.currentTarget.open;
        setOpen(nextOpen);
        if (nextOpen) void loadPending();
      }}
    >
      <summary className="cursor-pointer text-sm font-medium">
        Invite people <span className="text-xs text-muted">(directory)</span>
      </summary>
      {open ? (
        <div className="mt-4 flex flex-col gap-4">
          <p className="max-w-2xl text-sm leading-6 text-muted">
            Search colleagues who have opted into the directory. Invitations grant ordinary Member
            access after acceptance; promote them to Manager separately from the roster.
          </p>
          {error ? <Alert tone="error">{error}</Alert> : null}
          {notice ? (
            <p className="text-sm text-good" role="status">
              {notice}
            </p>
          ) : null}
          <form
            className="flex flex-wrap items-end gap-3"
            aria-label="Search operator directory"
            onSubmit={(event) => {
              event.preventDefault();
              void search();
            }}
          >
            <div className="min-w-48 flex-1">
              <TextField
                label="Find a person"
                hint="Name, username or organisation"
                minLength={2}
                maxLength={80}
                value={query}
                disabled={busy}
                onChange={(event) => setQuery(event.target.value)}
              />
            </div>
            <Button type="submit" busy={busy} disabled={query.trim().length < 2}>
              Search
            </Button>
          </form>
          <TextAreaField
            label="Optional note"
            hint="Keep it short. No email is sent by this first-release flow."
            maxLength={280}
            rows={2}
            value={note}
            disabled={busy}
            onChange={(event) => setNote(event.target.value)}
          />
          {results ? (
            <div className="border border-line/70" aria-live="polite">
              {results.items.length === 0 ? (
                <p className="p-4 text-sm text-muted">No discoverable accounts matched.</p>
              ) : (
                <ul className="divide-y divide-line/70">
                  {results.items.map((person) => {
                    const alreadyPending = pending.some(
                      (invitation) => invitation.recipient_id === person.user_id,
                    );
                    return (
                      <li
                        key={person.user_id}
                        className="flex flex-wrap items-center justify-between gap-3 p-4"
                      >
                        <div className="flex items-center gap-3">
                          <DirectoryAvatar
                            avatarUrl={person.avatar_url}
                            name={person.display_name}
                            size={36}
                          />
                          <div>
                            <p className="font-medium">{person.display_name}</p>
                            <p className="text-xs text-muted">
                              @{person.username}
                              {person.organisation ? ` · ${person.organisation}` : ''}
                            </p>
                          </div>
                        </div>
                        <Button
                          variant="secondary"
                          busy={busy}
                          disabled={alreadyPending}
                          onClick={() => void invite(person.user_id)}
                        >
                          {alreadyPending ? 'Invited' : 'Invite as member'}
                        </Button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          ) : null}
          {pending.length > 0 ? (
            <section aria-labelledby="pending-invitations-heading">
              <h4 id="pending-invitations-heading" className="text-sm font-semibold">
                Pending invitations ({pending.length})
              </h4>
              <ul className="mt-2 divide-y divide-line/70 border-y border-line/70">
                {pending.map((invitation) => (
                  <li
                    key={invitation.id}
                    className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm"
                  >
                    <span>
                      {invitation.recipient_display_name ?? 'Directory account'}{' '}
                      {invitation.recipient_username ? `(@${invitation.recipient_username}) ` : ''}
                      <span className="text-muted">{expiryLabel(invitation.expires_at)}</span>
                    </span>
                    <Button variant="ghost" busy={busy} onClick={() => void withdraw(invitation)}>
                      Withdraw
                    </Button>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      ) : null}
    </details>
  );
}
