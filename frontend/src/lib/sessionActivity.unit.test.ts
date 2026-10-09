import { expect, it } from 'vitest';

import { sessionActivity } from '@/test/fixtures';

import {
  idleDuration,
  idleRemaining,
  isGenuineActivity,
  nextActivityAt,
  showIdleWarning,
} from './sessionActivity';

const NOW = Date.parse('2026-10-09T12:00:00Z');

it('counts down from server time even when the device clock is a day ahead', () => {
  const snapshot = { data: sessionActivity(NOW), receivedAt: NOW + 86_400_000 };
  expect(idleRemaining(snapshot, snapshot.receivedAt)).toBe(180 * 60_000);
  expect(idleRemaining(snapshot, snapshot.receivedAt + 60_000)).toBe(179 * 60_000);
  expect(nextActivityAt(snapshot)).toBe(snapshot.receivedAt + 60_000);
});

it('warns five minutes before expiry and uses a minute of inactivity for the minimum limit', () => {
  const normal = { data: sessionActivity(NOW), receivedAt: NOW };
  expect(showIdleWarning(normal, NOW + 175 * 60_000 - 1)).toBe(false);
  expect(showIdleWarning(normal, NOW + 175 * 60_000)).toBe(true);
  const minimum = { data: sessionActivity(NOW, 5), receivedAt: NOW };
  expect(showIdleWarning(minimum, NOW + 59_999)).toBe(false);
  expect(showIdleWarning(minimum, NOW + 60_000)).toBe(true);
});

it.each(['pointerdown', 'keydown', 'touchstart', 'wheel', 'scroll', 'focus', 'mousemove'])(
  'accepts trusted %s but ignores synthetic events',
  (type) => {
    expect(isGenuineActivity({ type, isTrusted: true })).toBe(true);
    expect(isGenuineActivity({ type, isTrusted: false })).toBe(false);
  },
);

it('ignores visibility and timer events and describes the configured duration', () => {
  expect(isGenuineActivity({ type: 'visibilitychange', isTrusted: true })).toBe(false);
  expect(isGenuineActivity({ type: 'timer', isTrusted: true })).toBe(false);
  expect(idleDuration(180)).toBe('3 hours');
  expect(idleDuration(60)).toBe('1 hour');
  expect(idleDuration(15)).toBe('15 minutes');
});
