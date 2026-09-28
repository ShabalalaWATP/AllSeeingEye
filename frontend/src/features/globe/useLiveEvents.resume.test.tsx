import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { useEventsStore } from '@/stores/events';
import { FakeEventStreamClient } from '@/test/fakeStream';

import { useLiveEvents } from './useLiveEvents';

vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

const SNAPSHOT_REQUIRED = '{"reason":"snapshot_required"}';

beforeEach(() => {
  FakeEventStreamClient.reset();
  useEventsStore.getState().reset();
});

afterEach(() => {
  useEventsStore.getState().reset();
  FakeEventStreamClient.reset();
  vi.restoreAllMocks();
});

function mount() {
  const load = vi.spyOn(useEventsStore.getState(), 'load').mockResolvedValue();
  const handled = vi.spyOn(useEventsStore.getState(), 'handleStreamMessage');
  const view = renderHook(() => useLiveEvents());
  const client = FakeEventStreamClient.instances[0]!;
  return { load, handled, client, unmount: view.unmount };
}

it('skips the snapshot only when the server confirms a resume', () => {
  const { load, client, unmount } = mount();
  expect(load).toHaveBeenCalledOnce();
  act(() => {
    useEventsStore.setState({ loaded: true });
    client.connect(true, 'ab-9');
  });
  expect(load).toHaveBeenCalledOnce();
  act(() => {
    client.connect(false, 'ab-12');
  });
  expect(load).toHaveBeenCalledTimes(2);
  for (const data of ['not json', '{"resumed":"yes"}', '{"expires_in":900}']) {
    act(() => {
      client.emit({ event: 'hello', data, id: 'ab-13' });
    });
  }
  expect(load).toHaveBeenCalledTimes(5);
  unmount();
});

it('reloads a resumed stream whose mirror is not healthy', () => {
  const { load, client, unmount } = mount();
  load.mockClear();
  act(() => {
    // The first snapshot never finished loading.
    client.connect(true, 'ab-1');
  });
  expect(load).toHaveBeenCalledOnce();
  act(() => {
    useEventsStore.setState({ loaded: true, error: 'Network error' });
    client.connect(true, 'ab-2');
  });
  expect(load).toHaveBeenCalledTimes(2);
  act(() => {
    // A snapshot already in flight carries the replay in its reconciliation journal.
    useEventsStore.setState({ loaded: false, loading: true, error: null });
    client.connect(true, 'ab-3');
  });
  expect(load).toHaveBeenCalledTimes(2);
  unmount();
});

it('borrows the session token and refreshes it when the stream asks', async () => {
  const refresh = vi.spyOn(useAuthStore.getState(), 'refresh').mockResolvedValue('fresh');
  const { client, unmount } = mount();
  useAuthStore.setState({ accessToken: null });
  await expect(client.options.getToken(false)).resolves.toBe('fresh');
  useAuthStore.setState({ accessToken: 'current' });
  await expect(client.options.getToken(false)).resolves.toBe('current');
  await expect(client.options.getToken(true)).resolves.toBe('fresh');
  expect(refresh).toHaveBeenCalledTimes(2);
  useAuthStore.setState({ accessToken: null });
  unmount();
});

it('drops only the resync that repeats an unresumed hello position', () => {
  const { handled, client, unmount } = mount();
  handled.mockImplementation(() => undefined);
  act(() => {
    client.hello(false, 'ab-4');
    client.emit({ event: 'event.resync', data: SNAPSHOT_REQUIRED, id: 'ab-4' });
  });
  expect(handled).not.toHaveBeenCalled();
  act(() => {
    // Not directly after the hello any more, so it is a real refresh request.
    client.emit({ event: 'event.resync', data: SNAPSHOT_REQUIRED, id: 'ab-4' });
    client.hello(false, 'ab-5');
    client.emit({ event: 'event.resync', data: SNAPSHOT_REQUIRED, id: 'ab-6' });
    client.hello(false, null);
    client.emit({ event: 'event.resync', data: SNAPSHOT_REQUIRED, id: null });
  });
  expect(handled).toHaveBeenCalledTimes(3);
  act(() => {
    useEventsStore.setState({ loaded: true });
    client.hello(true, 'ab-7');
    client.emit({ event: 'event.resync', data: SNAPSHOT_REQUIRED, id: 'ab-7' });
  });
  expect(handled).toHaveBeenCalledTimes(4);
  unmount();
});
