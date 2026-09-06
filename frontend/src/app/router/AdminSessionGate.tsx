import { useEffect, useState } from 'react';
import { Link, Outlet } from 'react-router';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { LoadingScreen } from '@/components/ui/LoadingScreen';
import { verifySession } from '@/lib/api/auth';
import { isApiError } from '@/lib/api/errors';
import { selectIsAdmin, useAuthStore } from '@/stores/auth';

const CHECK_INTERVAL = 30_000;
const CHECK_TIMEOUT = 15_000;
interface Verification {
  userId: string;
  token: string;
  status: 'verified' | 'error';
}

/** Fresh authority for the dedicated admin area, never inferred from cached navigation.
 * Background checks preserve mounted drafts until a failure is observed. A changed
 * session always hides the outlet until its own verification completes.
 */
export default function AdminSessionGate() {
  const userId = useAuthStore((state) => state.user?.id);
  const token = useAuthStore((state) => state.accessToken);
  const isAdmin = useAuthStore(selectIsAdmin);
  const [verification, setVerification] = useState<Verification | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!isAdmin || userId === undefined || token === null) return;
    let live = true;
    let active: AbortController | null = null;
    const current = () => {
      const state = useAuthStore.getState();
      return (
        live && state.user?.id === userId && state.accessToken === token && selectIsAdmin(state)
      );
    };
    const verify = async () => {
      if (active !== null || !current()) return;
      const controller = new AbortController();
      active = controller;
      const timeout = window.setTimeout(() => controller.abort(), CHECK_TIMEOUT);
      try {
        const user = await verifySession(token, controller.signal);
        if (!current() || controller.signal.aborted) return;
        if (user.id !== userId) {
          setVerification({ userId, token, status: 'error' });
          return;
        }
        if (!user.is_active) {
          useAuthStore.getState().clearSession();
          return;
        }
        // This does not fabricate a new token or extend its expiry. Fresh non-admin
        // authority updates the shared store, removing admin navigation as well.
        useAuthStore.setState({ user });
        setVerification({ userId, token, status: 'verified' });
      } catch (error) {
        if (!current()) return;
        if (isApiError(error) && error.status === 401) {
          useAuthStore.getState().clearSession();
        } else {
          setVerification({ userId, token, status: 'error' });
        }
      } finally {
        window.clearTimeout(timeout);
        active = null;
      }
    };
    const visibleCheck = () => {
      if (document.visibilityState === 'visible') void verify();
    };
    void verify();
    window.addEventListener('focus', visibleCheck);
    document.addEventListener('visibilitychange', visibleCheck);
    const timer = window.setInterval(visibleCheck, CHECK_INTERVAL);
    return () => {
      live = false;
      active?.abort();
      window.clearInterval(timer);
      window.removeEventListener('focus', visibleCheck);
      document.removeEventListener('visibilitychange', visibleCheck);
    };
  }, [userId, token, isAdmin, attempt]);

  if (!isAdmin || token === null) {
    return (
      <div className="p-6">
        <Alert tone="warning" title="Administrator access required">
          Your current session does not have administrator access.
        </Alert>
        <Link to="/" className="mt-4 inline-flex min-h-11 items-center text-ember underline">
          Return to research
        </Link>
      </div>
    );
  }
  if (verification === null || verification.userId !== userId || verification.token !== token) {
    return <LoadingScreen label="Verifying administrator access" />;
  }
  if (verification.status === 'error') {
    return (
      <div className="space-y-4 p-6">
        <Alert tone="warning" title="Administrator access could not be verified">
          Protected content is hidden until the server confirms your current session.
        </Alert>
        <Button
          onClick={() => {
            setVerification(null);
            setAttempt((value) => value + 1);
          }}
        >
          Retry
        </Button>
        <Link to="/" className="ml-4 inline-flex min-h-11 items-center text-ember underline">
          Return to research
        </Link>
      </div>
    );
  }
  return <Outlet />;
}
