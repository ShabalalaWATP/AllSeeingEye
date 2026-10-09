import { act, render, renderHook } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';

import { sessionIdentity } from '@/lib/sessionIdentity';
import * as authApi from '@/lib/api/auth';
import { CSRF_VALUE, plainUser, sessionActivity, tokenFor } from '@/test/fixtures';
import { setCsrfCookie } from '@/test/env';

import { useAuthStore } from './auth';
import { useSessionActivity } from './useSessionActivity';

const NOW = Date.parse('2026-10-09T12:00:00Z');
const reportActivity = useAuthStore.getState().reportActivity;
class Channel {
  static current: Channel;
  onmessage: ((event: MessageEvent<unknown>) => void) | null = null;
  postMessage = vi.fn<(message: { type: 'confirmed' | 'expired' }) => void>();
  close = vi.fn();
  constructor() {
    Channel.current = this;
  }
}

function start() {
  vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] });
  vi.setSystemTime(NOW);
  setCsrfCookie(CSRF_VALUE);
  vi.stubGlobal('BroadcastChannel', Channel);
  const token = tokenFor(plainUser);
  useAuthStore.getState().setSession(token);
  return token;
}

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  useAuthStore.setState({ reportActivity });
});

it('ignores polling ticks, visibility changes and synthetic input without touching activity', () => {
  start();
  const report = vi.spyOn(useAuthStore.getState(), 'reportActivity').mockResolvedValue(true);
  const view = renderHook(() => useSessionActivity());
  act(() => {
    vi.advanceTimersByTime(61_000);
    document.dispatchEvent(new Event('visibilitychange'));
    document.dispatchEvent(new Event('pointerdown'));
    window.dispatchEvent(new Event('focus'));
  });
  expect(report).not.toHaveBeenCalled();
  expect(useAuthStore.getState().activity?.data.last_activity_at).toBe(new Date(NOW).toISOString());
  view.unmount();
  expect(Channel.current.close).toHaveBeenCalledOnce();
});

it('shares confirmed activity only with the same account and login family, without storage', () => {
  const token = start();
  renderHook(() => useSessionActivity());
  const identity = sessionIdentity(token.access_token)!;
  const localWrite = vi.spyOn(Storage.prototype, 'setItem');
  const activity = sessionActivity(NOW + 120_000);
  const message = { type: 'confirmed', ...identity, activity, receivedAt: NOW + 120_000 };
  act(() => {
    vi.setSystemTime(NOW + 120_000);
    Channel.current.onmessage?.({
      data: { ...message, familyId: 'another-login' },
    } as MessageEvent<unknown>);
  });
  expect(useAuthStore.getState().activity?.data).toEqual(token.activity);
  act(() => {
    Channel.current.onmessage?.({ data: message } as MessageEvent<unknown>);
  });
  expect(useAuthStore.getState().activity?.data).toEqual(activity);
  act(() => {
    Channel.current.onmessage?.({
      data: { ...message, activity: token.activity },
    } as MessageEvent<unknown>);
  });
  expect(useAuthStore.getState().activity?.data).toEqual(activity);
  expect(localWrite).not.toHaveBeenCalled();
  expect(JSON.stringify(Channel.current.postMessage.mock.calls)).not.toContain(token.access_token);
});

it('defers genuine activity until the minute boundary and never creates activity from later ticks', () => {
  start();
  const listen = vi.spyOn(document, 'addEventListener');
  const report = vi.spyOn(useAuthStore.getState(), 'reportActivity').mockResolvedValue(true);
  renderHook(() => useSessionActivity());
  const listener = listen.mock.calls.find(([event]) => event === 'pointerdown')?.[1];
  expect(typeof listener).toBe('function');
  act(() => {
    vi.advanceTimersByTime(30_000);
    if (typeof listener === 'function') listener({ type: 'pointerdown', isTrusted: true } as Event);
  });
  expect(report).not.toHaveBeenCalled();
  act(() => {
    vi.advanceTimersByTime(30_000);
  });
  expect(report).toHaveBeenCalledOnce();
  act(() => {
    vi.advanceTimersByTime(120_000);
  });
  expect(report).toHaveBeenCalledOnce();
});

it('retains per-tab idle enforcement when BroadcastChannel is unavailable', async () => {
  start();
  vi.stubGlobal('BroadcastChannel', undefined);
  renderHook(() => useSessionActivity());
  act(() => {
    vi.setSystemTime(NOW + 180 * 60_000);
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await act(async () => {
    await useAuthStore.getState().pendingIdleCheck;
  });
  expect(useAuthStore.getState().status).toBe('anonymous');
  await useAuthStore.getState().pendingLogout;
});

it('leaves the warning choices explicit instead of extending on their pointer or keyboard events', () => {
  start();
  const listen = vi.spyOn(document, 'addEventListener');
  const report = vi.spyOn(useAuthStore.getState(), 'reportActivity').mockResolvedValue(true);
  renderHook(() => useSessionActivity());
  render(<div data-session-idle-warning="true" />);
  const listener = listen.mock.calls.find(([event]) => event === 'pointerdown')?.[1];
  act(() => {
    vi.advanceTimersByTime(61_000);
    if (typeof listener === 'function') listener({ type: 'pointerdown', isTrusted: true } as Event);
    vi.advanceTimersByTime(60_000);
  });
  expect(report).not.toHaveBeenCalled();
});

it('ignores browser-generated scrolling without a recent trusted user gesture', () => {
  const token = start();
  const listen = vi.spyOn(document, 'addEventListener');
  const report = vi.spyOn(useAuthStore.getState(), 'reportActivity').mockResolvedValue(true);
  renderHook(() => useSessionActivity());
  const scroll = listen.mock.calls.find(([event]) => event === 'scroll')?.[1];
  act(() => {
    vi.advanceTimersByTime(61_000);
    // scrollTo/scrollIntoView can cause an isTrusted=true browser scroll event.
    if (typeof scroll === 'function') scroll({ type: 'scroll', isTrusted: true } as Event);
    vi.advanceTimersByTime(60_000);
  });
  expect(report).not.toHaveBeenCalled();
  expect(useAuthStore.getState().activity?.data).toEqual(token.activity);
});

it('does not tell other tabs to expire until the server confirms expiry', async () => {
  start();
  let resolve!: (value: null) => void;
  const response = new Promise<null>((done) => {
    resolve = done;
  });
  vi.spyOn(authApi, 'checkIdleExpiry').mockReturnValue(response);
  renderHook(() => useSessionActivity());
  act(() => {
    vi.setSystemTime(NOW + 180 * 60_000);
    document.dispatchEvent(new Event('visibilitychange'));
  });
  expect(
    Channel.current.postMessage.mock.calls.some(([message]) => message.type === 'expired'),
  ).toBe(false);
  await act(async () => {
    resolve(null);
    await useAuthStore.getState().pendingIdleCheck;
  });
  expect(
    Channel.current.postMessage.mock.calls.some(([message]) => message.type === 'expired'),
  ).toBe(true);
});

it('rejects malformed or stale broadcast expiry and rechecks a matching expiry with the server', async () => {
  const token = start();
  const check = vi.spyOn(authApi, 'checkIdleExpiry').mockResolvedValue(token.activity);
  const view = renderHook(() => useSessionActivity());
  const receive = Channel.current.onmessage!;
  const identity = sessionIdentity(token.access_token)!;
  const message = { type: 'expired', ...identity, activity: token.activity, receivedAt: NOW };
  act(() => {
    receive({ data: 'invalid' } as MessageEvent<unknown>);
    receive({ data: { ...message, receivedAt: NOW + 1 } } as MessageEvent<unknown>);
    receive({ data: { ...message, activity: sessionActivity(NOW - 1) } } as MessageEvent<unknown>);
  });
  expect(check).not.toHaveBeenCalled();
  await act(async () => {
    receive({ data: message } as MessageEvent<unknown>);
    await useAuthStore.getState().pendingIdleCheck;
  });
  expect(check).toHaveBeenCalledOnce();
  expect(useAuthStore.getState().status).toBe('authenticated');
  view.unmount();
  receive({ data: message } as MessageEvent<unknown>);
  expect(check).toHaveBeenCalledOnce();
});
