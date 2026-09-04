/**
 * Session state. The access token lives only in memory (never in storage); the
 * refresh token is an HttpOnly cookie the browser sends on its own. Refreshes are
 * deduplicated so concurrent 401s (or StrictMode double effects) never present
 * the same rotated refresh token twice, which the backend treats as reuse.
 */
import { create } from 'zustand';

import * as authApi from '@/lib/api/auth';
import { bindSession } from '@/lib/api/client';
import type { TokenResponse, User } from '@/lib/api/schemas';

export type AuthStatus = 'unknown' | 'anonymous' | 'authenticated';

export interface AuthState {
  status: AuthStatus;
  user: User | null;
  accessToken: string | null;
  pendingRefresh: Promise<string | null> | null;
  bootstrap: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
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

export const useAuthStore = create<AuthState>()((set, get) => ({
  ...initialAuthState,

  setSession: (token) => {
    set({ status: 'authenticated', user: token.user, accessToken: token.access_token });
  },

  clearSession: () => {
    set({ status: 'anonymous', user: null, accessToken: null });
  },

  refresh: () => {
    const pending = get().pendingRefresh;
    if (pending !== null) return pending;
    const attempt = authApi
      .refreshSession()
      .then((token) => {
        get().setSession(token);
        return token.access_token;
      })
      .catch(() => {
        get().clearSession();
        return null;
      })
      .finally(() => {
        set({ pendingRefresh: null });
      });
    set({ pendingRefresh: attempt });
    return attempt;
  },

  bootstrap: async () => {
    await get().refresh();
  },

  login: async (email, password) => {
    const token = await authApi.login(email, password);
    get().setSession(token);
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

export const selectIsAdmin = (state: AuthState): boolean => state.user?.role === 'admin';
