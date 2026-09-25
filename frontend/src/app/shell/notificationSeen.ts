/**
 * When each account last opened the notification bell, kept per user in this browser.
 * The first read starts the clock, so older finished research never floods a new bell.
 */
import { readStored, writeStored } from '@/lib/safeStorage';

const PREFIX = 'ase-notifications-seen:';

export function seenKey(userId: string): string {
  return `${PREFIX}${userId}`;
}

export function markNotificationsSeen(userId: string, at: number = Date.now()): number {
  writeStored(seenKey(userId), String(at));
  return at;
}

export function notificationsSeenAt(userId: string, now: number = Date.now()): number {
  const stored = Number(readStored(seenKey(userId)) ?? Number.NaN);
  return Number.isFinite(stored) && stored > 0 ? stored : markNotificationsSeen(userId, now);
}
