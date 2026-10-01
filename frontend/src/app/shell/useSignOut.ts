import { useNavigate } from 'react-router';

import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useAuthStore } from '@/stores/auth';

/**
 * Ends the session and returns to sign-in. The store clears the local session even when
 * the server cannot record the sign-out, so `error` only reports a failed return.
 */
export function useSignOut() {
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();
  const { run, busy, error } = useAsyncAction(async () => {
    await logout();
    await navigate('/login', { replace: true });
  });
  return { signOut: run, busy, failed: error !== null };
}
