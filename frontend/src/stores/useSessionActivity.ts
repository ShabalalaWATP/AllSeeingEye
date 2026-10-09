import { useEffect, useState } from 'react';
import { z } from 'zod';

import { idleRemaining, isGenuineActivity, sessionActivitySchema } from '@/lib/sessionActivity';
import { sessionIdentity } from '@/lib/sessionIdentity';

import { useAuthStore } from './auth';

const channelMessage = z.object({
  type: z.enum(['confirmed', 'expired']),
  userId: z.string(),
  familyId: z.string(),
  activity: sessionActivitySchema,
  receivedAt: z.number(),
});
const ACTIVITY_EVENTS = ['pointerdown', 'keydown', 'touchstart', 'wheel', 'scroll', 'mousemove'];
const SCROLL_GESTURES = ['pointerdown', 'keydown', 'touchstart', 'wheel'];

/** One activity observer for the protected workspace, with no persisted browser state. */
export function useSessionActivity(): number {
  const generation = useAuthStore((state) => state.sessionGeneration);
  const authenticated = useAuthStore((state) => state.status === 'authenticated');
  const [now, setNow] = useState(Date.now);

  useEffect(() => {
    if (!authenticated) return;
    const original = useAuthStore.getState().accessToken;
    const owner = original === null ? null : sessionIdentity(original);
    if (owner === null) return;
    let alive = true;
    let pendingAt: number | null = null;
    let lastMotion = 0;
    let lastScrollGesture = -Infinity;
    let channel: BroadcastChannel | null = null;
    try {
      if (typeof BroadcastChannel !== 'undefined')
        channel = new BroadcastChannel('ase-session-activity');
    } catch {
      /* Per-tab enforcement remains available without BroadcastChannel. */
    }
    const current = () =>
      alive &&
      useAuthStore.getState().status === 'authenticated' &&
      useAuthStore.getState().sessionGeneration === generation;
    const publish = (
      type: 'confirmed' | 'expired',
      state: ReturnType<typeof useAuthStore.getState>,
    ) => {
      if (state.activity === null) return;
      try {
        channel?.postMessage({
          type,
          ...owner,
          activity: state.activity.data,
          receivedAt: state.activity.receivedAt,
        });
      } catch {
        /* A suspended/closed channel must not break local expiry. */
      }
    };
    if (channel !== null)
      channel.onmessage = (event: MessageEvent<unknown>) => {
        if (!current()) return;
        const parsed = channelMessage.safeParse(event.data);
        if (!parsed.success) return;
        const message = parsed.data;
        if (
          message.userId !== owner.userId ||
          message.familyId !== owner.familyId ||
          message.receivedAt > Date.now()
        )
          return;
        const store = useAuthStore.getState();
        if (message.type === 'confirmed') {
          store.confirmActivity(message.activity, message.receivedAt);
        } else if (
          store.activity?.data.last_activity_at === message.activity.last_activity_at &&
          store.activity.data.idle_expires_at === message.activity.idle_expires_at
        ) {
          void store.expireIdleSession();
        }
      };
    const unsubscribe = useAuthStore.subscribe((state, previous) => {
      if (previous.sessionGeneration !== generation) return;
      if (state.status === 'anonymous' && state.idleExpiryConfirmed) publish('expired', previous);
      else if (state.sessionGeneration === generation && state.activity !== previous.activity)
        publish('confirmed', state);
    });
    publish('confirmed', useAuthStore.getState());
    const check = () => {
      if (!current()) return;
      const store = useAuthStore.getState();
      const time = Date.now();
      setNow(time);
      if (store.activity !== null && idleRemaining(store.activity, time) <= 0) {
        void store.expireIdleSession();
        return;
      }
      // Choosing Sign out or navigating the warning must not extend the session.
      if (document.querySelector('[data-session-idle-warning]') !== null) pendingAt = null;
      if (
        pendingAt !== null &&
        time >= store.activityRetryAt &&
        store.pendingActivity === null &&
        document.visibilityState === 'visible'
      ) {
        pendingAt = null;
        void store.reportActivity();
      }
    };
    const observe = (event: Event) => {
      if (!current() || !isGenuineActivity(event) || document.visibilityState !== 'visible') return;
      if (document.querySelector('[data-session-idle-warning]') !== null) return;
      // Ignore element focus and the focus restoration performed by modal dialogs.
      if (event.type === 'focus' && event.target !== window) return;
      const time = Date.now();
      // Browser-generated scroll events can also follow polling-driven scrollTo.
      // Only a recent physical gesture makes a scroll relevant to session activity.
      if (event.type === 'scroll' && time - lastScrollGesture > 1500) return;
      if (SCROLL_GESTURES.includes(event.type)) lastScrollGesture = time;
      if (event.type === 'mousemove') {
        if (time - lastMotion < 1000) return;
        lastMotion = time;
      }
      pendingAt = time;
      check();
    };
    const resume = () => {
      if (document.visibilityState === 'visible') check();
    };
    for (const event of ACTIVITY_EVENTS)
      document.addEventListener(event, observe, { passive: true, capture: true });
    window.addEventListener('focus', observe);
    document.addEventListener('visibilitychange', resume);
    const timer = window.setInterval(check, 1000);
    // A suspended tab may resume beyond the deadline before its first timer fires.
    check();
    return () => {
      alive = false;
      window.clearInterval(timer);
      for (const event of ACTIVITY_EVENTS) document.removeEventListener(event, observe, true);
      window.removeEventListener('focus', observe);
      document.removeEventListener('visibilitychange', resume);
      unsubscribe();
      channel?.close();
    };
  }, [authenticated, generation]);

  return now;
}
