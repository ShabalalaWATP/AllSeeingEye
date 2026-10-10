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
import { isApiError, sessionChangedError } from '@/lib/api/errors';
import { CSRF_COOKIE, readCookie } from '@/lib/csrf';
import type { TokenResponse, User } from '@/lib/api/schemas';
import { clearBrowserPush } from '@/lib/browserPush';
import { responseIdentity, sessionIdentity } from '@/lib/sessionIdentity';
import { activityActions, initialActivityState, type ActivityState } from './authActivity';
import { nextActivityAt, parseIdleMinutes } from '@/lib/sessionActivity';

export type AuthStatus = 'unknown' | 'anonymous' | 'authenticated';

export interface AuthState extends ActivityState {
  status: AuthStatus;
  user: User | null;
  accessToken: string | null;
  /** Stable through refresh rotations; changes for each explicit login or clear. */
  sessionGeneration: number;
  pendingRefresh: Promise<string | null> | null;
  pendingLogout: Promise<void> | null;
  sessionCsrf: string | null;
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
  sessionGeneration: 0,
  pendingRefresh: null,
  pendingLogout: null,
  sessionCsrf: null,
  ...initialActivityState,
};

const REFRESH_LOCK = 'ase-refresh';
// Never reuse generations, including when a test or development preview resets state.
let nextSessionGeneration = 0;

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
  ...activityActions(set, get),

  setSession: (token) => {
    responseIdentity(token);
    const activity = { data: token.activity, receivedAt: Date.now() };
    set({
      ...initialActivityState,
      status: 'authenticated',
      user: token.user,
      accessToken: token.access_token,
      sessionGeneration: ++nextSessionGeneration,
      pendingRefresh: null,
      activity,
      activityRetryAt: nextActivityAt(activity),
      activityError: null,
      pendingActivity: null,
      idleExpiredMinutes: null,
      sessionCsrf: readCookie(CSRF_COOKIE),
    });
  },

  clearSession: () => {
    // A different tab may now own the shared browser subscription and cookies.
    if (get().sessionCsrf === readCookie(CSRF_COOKIE)) {
      void clearBrowserPush().catch(() => {
        /* The revoked server session also prevents delivery. */
      });
    }
    set({
      status: 'anonymous',
      user: null,
      accessToken: null,
      sessionGeneration: ++nextSessionGeneration,
      pendingRefresh: null,
      activity: null,
      activityRetryAt: 0,
      activityError: null,
      pendingActivity: null,
      sessionCsrf: null,
      idleCheckRetryAt: 0,
    });
  },

  refresh: () => {
    const owner = get();
    const pending = owner.pendingRefresh;
    if (pending !== null) return pending;
    const expected = owner.accessToken === null ? null : sessionIdentity(owner.accessToken);
    // Do not turn an unrecognised authenticated session into a cookie-only bootstrap.
    if (
      owner.status === 'authenticated' &&
      (expected === null || expected.userId !== owner.user?.id)
    ) {
      return Promise.resolve(null);
    }
    const current = () =>
      get().sessionGeneration === owner.sessionGeneration && get().user?.id === owner.user?.id;
    const csrf = readCookie(CSRF_COOKIE);
    const attempt = withRefreshLock(() =>
      current() ? authApi.refreshSession() : Promise.resolve(null),
    )
      .then((token) => {
        if (!current() || token === null) return null;
        const identity = responseIdentity(token);
        if (expected !== null) {
          if (identity.userId !== expected.userId || identity.familyId !== expected.familyId)
            return null;
          // Rotation belongs to the same login, so concurrent requests keep their owner.
          set({ status: 'authenticated', user: token.user, accessToken: token.access_token });
          get().confirmActivity(token.activity);
          set({ sessionCsrf: readCookie(CSRF_COOKIE) });
        } else {
          get().setSession(token);
        }
        return token.access_token;
      })
      .catch((error: unknown) => {
        if (current() && readCookie(CSRF_COOKIE) === csrf && rejectsSession(error)) {
          if (isApiError(error) && error.code === 'session_idle_expired') {
            void get().expireIdleSession(parseIdleMinutes(error.fields.idle_minutes));
          } else get().clearSession();
        }
        return null;
      })
      .finally(() => {
        if (get().pendingRefresh === attempt) set({ pendingRefresh: null });
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
    const generation = ++nextSessionGeneration;
    set({ sessionGeneration: generation, pendingRefresh: null });
    // An older logout response deletes shared cookies. Let it finish before login sets new ones.
    const pendingLogout = get().pendingLogout;
    if (pendingLogout !== null) await pendingLogout;
    if (get().sessionGeneration !== generation) throw sessionChangedError();
    const result = await authApi.login(email, password);
    if (get().sessionGeneration !== generation) throw sessionChangedError();
    if ('mfa_required' in result) return result;
    get().setSession(result);
    return null;
  },

  logout: () => {
    const owner = get();
    const family =
      owner.accessToken === null ? undefined : sessionIdentity(owner.accessToken)?.familyId;
    const csrf = readCookie(CSRF_COOKIE);
    const pending = get().pendingLogout;
    if (pending !== null) {
      get().clearSession();
      return pending;
    }
    const attempt = Promise.resolve()
      .then(() =>
        withRefreshLock(() =>
          family !== undefined || readCookie(CSRF_COOKIE) === csrf
            ? authApi.logout(family)
            : Promise.resolve(),
        ),
      )
      .catch(() => {
        // The local session is cleared regardless of the server outcome.
      })
      .finally(() => {
        if (get().pendingLogout === attempt) set({ pendingLogout: null });
      });
    // Publish the cookie mutation before making the UI anonymous, so a new login waits.
    set({ pendingLogout: attempt });
    get().clearSession();
    return attempt;
  },
}));

bindSession({
  getAccessToken: () => useAuthStore.getState().accessToken,
  getSessionGeneration: () => useAuthStore.getState().sessionGeneration,
  refreshAccessToken: () => useAuthStore.getState().refresh(),
  onSessionLost: () => {
    useAuthStore.getState().clearSession();
  },
  onSessionIdle: (minutes) => {
    void useAuthStore.getState().expireIdleSession(minutes);
  },
});

export const selectIsAdmin = (state: AuthState): boolean =>
  state.status === 'authenticated' && state.user?.is_active === true && state.user.role === 'admin';
