import { useState } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import {
  fetchAccountSessions,
  revokeAccountSession,
  revokeOtherSessions,
} from '@/lib/api/accountSecurity';
import { describeError } from '@/lib/api/errors';
import { formatPersonalDate } from '@/lib/format';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useAuthStore } from '@/stores/auth';
import { useProfile } from '@/stores/profile';
import { useAccountRequest } from './useAccountRequest';

export function AccountSessions() {
  const sessions = useScopedResource(fetchAccountSessions);
  const { profile } = useProfile();
  const actorId = useAuthStore((state) => state.user?.id);
  const [selected, setSelected] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  const beginRequest = useAccountRequest();
  const action = useAsyncAction(async () => {
    if (!selected) return;
    const signal = beginRequest();
    const current = sessions.data?.items.find((item) => item.id === selected)?.current;
    if (selected === 'others') await revokeOtherSessions(signal);
    else await revokeAccountSession(selected, signal);
    if (signal.aborted) return;
    if (useAuthStore.getState().user?.id !== actorId) return;
    if (current) {
      useAuthStore.getState().clearSession();
      return;
    }
    setSelected(null);
    setNotice(
      selected === 'others'
        ? 'Other sessions have been signed out.'
        : 'The selected session has been signed out.',
    );
    await sessions.reload();
  });
  return (
    <section className="space-y-4 border-t border-line pt-6" aria-labelledby="sessions-title">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="sessions-title" className="text-xl font-semibold">
          Devices and sessions
        </h2>
        <Button
          variant="secondary"
          disabled={action.busy || !sessions.data?.items.some((item) => !item.current)}
          onClick={() => {
            setSelected('others');
            action.clearError();
          }}
        >
          Sign out other devices
        </Button>
      </div>
      <p className="text-sm text-muted">
        Review where you are signed in. Times show the latest sign-in or session renewal, not
        browsing activity.
      </p>
      {sessions.loading && <p role="status">Loading sessions...</p>}
      {sessions.error && (
        <>
          <Alert tone="error">{describeError(sessions.error)}</Alert>
          <Button variant="secondary" onClick={() => void sessions.reload()}>
            Retry sessions
          </Button>
        </>
      )}
      {action.error && <Alert tone="error">{describeError(action.error)}</Alert>}
      {notice && (
        <p role="status" className="text-sm text-muted">
          {notice}
        </p>
      )}
      {selected && (
        <div className="space-y-3 rounded border border-line p-4">
          <p className="text-sm">
            {selected === 'others'
              ? 'Sign out every other device? This session will stay signed in.'
              : 'Sign out the selected session? That device will need to sign in again.'}
          </p>
          <div className="flex gap-3">
            <Button variant="danger" busy={action.busy} onClick={() => void action.run()}>
              Confirm sign-out
            </Button>
            <Button variant="ghost" disabled={action.busy} onClick={() => setSelected(null)}>
              Cancel
            </Button>
          </div>
        </div>
      )}
      <ul className="divide-y divide-line">
        {sessions.data?.items.map((item) => (
          <li key={item.id} className="flex flex-wrap justify-between gap-4 py-4">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">
                {item.current ? 'This session' : 'Other session'}
              </p>
              <p className="mt-1 break-all text-xs text-muted">
                {item.user_agent?.trim() ? item.user_agent : 'Browser details unavailable'}
              </p>
              <p className="mt-2 text-xs text-muted">
                {item.ip?.trim() ? item.ip : 'IP unavailable'} ·{' '}
                {formatPersonalDate(item.last_active_at, profile)}
              </p>
            </div>
            <Button
              variant="ghost"
              disabled={action.busy}
              onClick={() => {
                setSelected(item.id);
                action.clearError();
              }}
            >
              Sign out {item.current ? 'this session' : 'session'}
            </Button>
          </li>
        ))}
      </ul>
      {sessions.data?.truncated && (
        <p className="text-xs text-muted">
          Showing 100 sessions. Sign out other devices applies to all your other sessions.
        </p>
      )}
      {sessions.data?.items.length === 0 && (
        <p className="text-sm text-muted">
          No active sessions were returned. Refresh to check again.
        </p>
      )}
    </section>
  );
}
