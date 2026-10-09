import * as authApi from '@/lib/api/auth';
import { describeError, isApiError } from '@/lib/api/errors';
import { sessionIdentity } from '@/lib/sessionIdentity';
import {
  ACTIVITY_INTERVAL,
  idleRemaining,
  nextActivityAt,
  parseIdleMinutes,
  type ConfirmedActivity,
  type SessionActivity,
} from '@/lib/sessionActivity';

import type { AuthState } from './auth';

export interface ActivityState {
  activity: ConfirmedActivity | null;
  activityRetryAt: number;
  activityError: string | null;
  pendingActivity: Promise<boolean> | null;
  pendingIdleCheck: Promise<void> | null;
  idleCheckRetryAt: number;
  idleExpiryConfirmed: boolean;
  idleExpiredMinutes: number | null;
  confirmActivity: (data: SessionActivity, receivedAt?: number) => void;
  reportActivity: () => Promise<boolean>;
  expireIdleSession: (minutes?: number) => Promise<void>;
}

export const initialActivityState = {
  activity: null,
  activityRetryAt: 0,
  activityError: null,
  pendingActivity: null,
  pendingIdleCheck: null,
  idleCheckRetryAt: 0,
  idleExpiryConfirmed: false,
  idleExpiredMinutes: null,
};

type SetState = (state: Partial<AuthState>) => void;

/** Activity belongs to a login generation, including refreshes and queued responses. */
export function activityActions(
  set: SetState,
  get: () => AuthState,
): Pick<ActivityState, 'confirmActivity' | 'reportActivity' | 'expireIdleSession'> {
  return {
    confirmActivity: (data, receivedAt = Date.now()) => {
      const previous = get().activity;
      if (previous !== null && Date.parse(data.server_now) < Date.parse(previous.data.server_now))
        return;
      if (
        previous !== null &&
        data.server_now === previous.data.server_now &&
        data.last_activity_at === previous.data.last_activity_at &&
        data.idle_expires_at === previous.data.idle_expires_at &&
        data.idle_minutes === previous.data.idle_minutes &&
        receivedAt >= previous.receivedAt
      )
        return;
      const activity = { data, receivedAt };
      set({
        activity,
        activityRetryAt: nextActivityAt(activity),
        activityError: null,
        idleCheckRetryAt: 0,
      });
    },

    reportActivity: () => {
      const owner = get();
      if (
        owner.status !== 'authenticated' ||
        owner.accessToken === null ||
        owner.activity === null
      ) {
        return Promise.resolve(false);
      }
      if (idleRemaining(owner.activity) <= 0) {
        return get()
          .expireIdleSession()
          .then(() => {
            const latest = get();
            return latest.status === 'authenticated' &&
              latest.sessionGeneration === owner.sessionGeneration &&
              latest.activity !== null &&
              idleRemaining(latest.activity) > 0
              ? latest.reportActivity()
              : false;
          });
      }
      if (owner.pendingActivity !== null) return owner.pendingActivity;
      if (Date.now() < owner.activityRetryAt) return Promise.resolve(false);
      const identity = sessionIdentity(owner.accessToken);
      if (identity === null || identity.userId !== owner.user?.id) return Promise.resolve(false);
      const accessToken = owner.accessToken;
      const current = () =>
        get().status === 'authenticated' && get().sessionGeneration === owner.sessionGeneration;
      const send = async () => {
        try {
          return await authApi.recordActivity(accessToken);
        } catch (error) {
          if (
            !current() ||
            !isApiError(error) ||
            error.status !== 401 ||
            error.code === 'session_idle_expired'
          )
            throw error;
          // An access JWT can expire while the idle family remains live. The store's
          // refresher verifies the original family and never marks background activity.
          const token = await get().refresh();
          if (token === null || !current()) return null;
          const refreshed = sessionIdentity(token);
          if (refreshed?.userId !== identity.userId || refreshed.familyId !== identity.familyId)
            return null;
          return authApi.recordActivity(token);
        }
      };
      const attempt = send()
        .then((data) => {
          if (!current() || data === null) return false;
          get().confirmActivity(data);
          return true;
        })
        .catch((error: unknown) => {
          if (!current()) return false;
          if (isApiError(error) && error.code === 'session_idle_expired') {
            void get().expireIdleSession(parseIdleMinutes(error.fields.idle_minutes));
          } else {
            const wait =
              isApiError(error) && error.status === 429
                ? (error.retryAfterSeconds ?? 60) * 1000
                : ACTIVITY_INTERVAL;
            set({ activityRetryAt: Date.now() + wait, activityError: describeError(error) });
          }
          return false;
        })
        .finally(() => {
          if (get().pendingActivity === attempt) set({ pendingActivity: null });
        });
      set({
        pendingActivity: attempt,
        activityRetryAt: Date.now() + ACTIVITY_INTERVAL,
        activityError: null,
      });
      return attempt;
    },

    expireIdleSession: (minutes) => {
      const owner = get();
      if (owner.status === 'anonymous') return Promise.resolve();
      if (owner.status === 'unknown') {
        set({ idleExpiredMinutes: minutes ?? 180 });
        get().clearSession();
        return Promise.resolve();
      }
      if (owner.pendingIdleCheck !== null) return owner.pendingIdleCheck;
      if (Date.now() < owner.idleCheckRetryAt) return Promise.resolve();
      const identity = owner.accessToken === null ? null : sessionIdentity(owner.accessToken);
      if (identity === null) return Promise.resolve();
      const current = () =>
        get().status === 'authenticated' && get().sessionGeneration === owner.sessionGeneration;
      const attempt = authApi
        .checkIdleExpiry(identity.familyId)
        .then((data) => {
          if (!current()) return;
          if (data !== null) {
            get().confirmActivity(data);
            set({ idleCheckRetryAt: 0, activityError: null });
            return;
          }
          set({
            idleExpiredMinutes: minutes ?? owner.activity?.data.idle_minutes ?? 180,
            idleExpiryConfirmed: true,
          });
          get().clearSession();
        })
        .catch((error: unknown) => {
          if (current())
            set({
              idleCheckRetryAt: Date.now() + ACTIVITY_INTERVAL,
              activityError: describeError(error),
            });
        })
        .finally(() => {
          if (get().pendingIdleCheck === attempt) set({ pendingIdleCheck: null });
        });
      set({ pendingIdleCheck: attempt, activityError: null });
      return attempt;
    },
  };
}
