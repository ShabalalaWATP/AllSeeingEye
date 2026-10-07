/**
 * Session state. The access token lives only in memory (never in storage); the
 * refresh token is an HttpOnly cookie the browser sends on its own. Refreshes are
 * deduplicated so concurrent 401s (or StrictMode double effects) never present
 * the same rotated refresh token twice, which the backend treats as reuse.
 *
 * Tabs share the cookie, so refreshes are also serialised across tabs with the Web
 * Locks API where the browser offers it. The browser reads the cookie when each
 * request is sent, so a tab that waited for the lock presents the cookie the previous
 * holder's response rotated, never the consumed one. Without Web Locks, concurrent
 * refreshes from two tabs can still trip reuse detection and end the session.
 *
 * Only a definite rejection (401 or 403) ends the local session. A network failure
 * or server error leaves it intact so a later request can retry the refresh.
 */
import { create } from 'zustand';

import * as authApi from '@/lib/api/auth';
import type { PendingMfa } from '@/lib/api/mfa';
import { bindSession } from '@/lib/api/client';
import { isApiError } from '@/lib/api/errors';
import { CSRF_COOKIE, readCookie } from '@/lib/csrf';
import type { TokenResponse, User } from '@/lib/api/schemas';
import { clearBrowserPush } from '@/lib/browserPush';

export type AuthStatus = 'unknown' | 'anonymous' | 'authenticated';

export interface AuthState {
  status: AuthStatus;
  user: User | null;
  accessToken: string | null;
  pendingRefresh: Promise<string | null> | null;
  bootstrap: () => Promise<void>;
  login: (email: string, password: string) => Promise<PendingMfa | null>;
  logout: () => Promise<void>;
  refresh: () => Promise<string | null>;
  setSession: (token: TokenResponse) => void;
  clearSession: () => void;
}

export const initialAuthState = {
  status: 'unknown' as AuthStatus,
  user: null,
  accessToken: null,
  pendingRefresh: null,
};

const REFRESH_LOCK = 'ase-refresh';

function rejectsSession(error: unknown): boolean {
  return isApiError(error) && (error.status === 401 || error.status === 403);
}

/** Runs `work` while holding the cross-tab refresh lock, or directly without Web Locks. */
function withRefreshLock<T>(work: () => Promise<T>): Promise<T> {
  const locks = typeof navigator === 'undefined' ? undefined : navigator.locks;
  if (typeof locks?.request !== 'function') return work();
  // The lock resolves with the callback's promise; `then` unwraps it for the type checker.
  return locks.request(REFRESH_LOCK, work).then((result) => result);
}

export const useAuthStore = create<AuthState>()((set, get) => ({
  ...initialAuthState,

  setSession: (token) => {
    set({ status: 'authenticated', user: token.user, accessToken: token.access_token });
  },

  clearSession: () => {
    void clearBrowserPush().catch(() => {
      /* The revoked server session also prevents delivery. */
    });
    set({ status: 'anonymous', user: null, accessToken: null });
  },

  refresh: () => {
    const pending = get().pendingRefresh;
    if (pending !== null) return pending;
    const attempt = withRefreshLock(() => authApi.refreshSession())
      .then((token) => {
        get().setSession(token);
        return token.access_token;
      })
      .catch((error: unknown) => {
        if (rejectsSession(error)) get().clearSession();
        return null;
      })
      .finally(() => {
        set({ pendingRefresh: null });
      });
    set({ pendingRefresh: attempt });
    return attempt;
  },

  bootstrap: async () => {
    // Without the CSRF cookie the refresh cannot succeed, so do not even ask.
    if (readCookie(CSRF_COOKIE) === null) {
      get().clearSession();
      return;
    }
    const token = await get().refresh();
    // A transient failure leaves no usable session, but keeps browser push intact.
    if (token === null && get().status === 'unknown') {
      set({ status: 'anonymous', user: null, accessToken: null });
    }
  },

  login: async (email, password) => {
    const result = await authApi.login(email, password);
    if ('mfa_required' in result) return result;
    get().setSession(result);
    return null;
  },

  logout: async () => {
    try {
      await authApi.logout();
    } catch {
      // The local session is cleared regardless of the server outcome.
    }
    get().clearSession();
  },
}));

bindSession({
  getAccessToken: () => useAuthStore.getState().accessToken,
  refreshAccessToken: () => useAuthStore.getState().refresh(),
  onSessionLost: () => {
    useAuthStore.getState().clearSession();
  },
});

export const selectIsAdmin = (state: AuthState): boolean =>
  state.status === 'authenticated' && state.user?.is_active === true && state.user.role === 'admin';
