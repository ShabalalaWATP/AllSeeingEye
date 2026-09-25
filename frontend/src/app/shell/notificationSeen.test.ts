import { afterEach, describe, expect, it, vi } from 'vitest';

import { markNotificationsSeen, notificationsSeenAt, seenKey } from './notificationSeen';

// Restore blocked storage before the shared clean-up writes to persisted stores.
afterEach(() => {
  vi.restoreAllMocks();
});

describe('notification last-seen time', () => {
  it('starts the clock on first read and keeps it per user', () => {
    expect(notificationsSeenAt('user-a', 1_000)).toBe(1_000);
    expect(localStorage.getItem(seenKey('user-a'))).toBe('1000');
    expect(notificationsSeenAt('user-a', 5_000)).toBe(1_000);
    expect(notificationsSeenAt('user-b', 7_000)).toBe(7_000);
  });

  it('moves forward when the bell is opened and replaces unusable values', () => {
    expect(markNotificationsSeen('user-a', 9_000)).toBe(9_000);
    expect(notificationsSeenAt('user-a', 10_000)).toBe(9_000);
    localStorage.setItem(seenKey('user-a'), 'not a time');
    expect(notificationsSeenAt('user-a', 11_000)).toBe(11_000);
    localStorage.setItem(seenKey('user-a'), '-5');
    expect(notificationsSeenAt('user-a', 12_000)).toBe(12_000);
  });

  it('falls back to the current time when storage is unavailable', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new DOMException('Blocked', 'SecurityError');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('Blocked', 'SecurityError');
    });
    expect(notificationsSeenAt('user-a', 3_000)).toBe(3_000);
    expect(markNotificationsSeen('user-a', 4_000)).toBe(4_000);
  });
});
