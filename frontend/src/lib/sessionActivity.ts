import { z } from 'zod';

import type { components } from './api/types.gen';

export type SessionActivity = components['schemas']['SessionActivityOut'];
export const sessionActivitySchema: z.ZodType<SessionActivity> = z
  .object({
    server_now: z.iso.datetime({ offset: true }),
    last_activity_at: z.iso.datetime({ offset: true }),
    idle_expires_at: z.iso.datetime({ offset: true }),
    idle_minutes: z.number().int().min(5).max(1440),
  })
  .refine(
    (value) =>
      Date.parse(value.last_activity_at) <= Date.parse(value.server_now) &&
      Date.parse(value.idle_expires_at) >= Date.parse(value.last_activity_at),
  );

/** Server time at observation, with local elapsed time used only for the countdown. */
export interface ConfirmedActivity {
  data: SessionActivity;
  receivedAt: number;
}

export const ACTIVITY_INTERVAL = 60_000;
export const IDLE_WARNING = 5 * 60_000;

export function idleRemaining(activity: ConfirmedActivity, now = Date.now()): number {
  return (
    Date.parse(activity.data.idle_expires_at) -
    Date.parse(activity.data.server_now) -
    Math.max(0, now - activity.receivedAt)
  );
}

export function nextActivityAt(activity: ConfirmedActivity): number {
  return (
    activity.receivedAt +
    Math.max(
      0,
      ACTIVITY_INTERVAL -
        (Date.parse(activity.data.server_now) - Date.parse(activity.data.last_activity_at)),
    )
  );
}

export function showIdleWarning(activity: ConfirmedActivity, now = Date.now()): boolean {
  const age =
    Date.parse(activity.data.server_now) -
    Date.parse(activity.data.last_activity_at) +
    Math.max(0, now - activity.receivedAt);
  // At the minimum five-minute limit, give Stay a full minute before warning again.
  return idleRemaining(activity, now) <= IDLE_WARNING && age >= ACTIVITY_INTERVAL;
}

export function idleDuration(minutes: number): string {
  return minutes % 60 === 0
    ? `${String(minutes / 60)} ${minutes === 60 ? 'hour' : 'hours'}`
    : `${String(minutes)} minutes`;
}

export { parseIdleMinutes } from './idleMinutes';

/** Ignore synthetic events. Visibility changes and timers only check the deadline. */
export function isGenuineActivity(event: Pick<Event, 'isTrusted' | 'type'>): boolean {
  return (
    event.isTrusted &&
    ['pointerdown', 'mousemove', 'keydown', 'wheel', 'touchstart', 'scroll', 'focus'].includes(
      event.type,
    )
  );
}
