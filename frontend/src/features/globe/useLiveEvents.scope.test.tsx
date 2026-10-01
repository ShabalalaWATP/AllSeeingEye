import { act, renderHook } from '@testing-library/react';
import { expect, it, vi } from 'vitest';

import { subscribeBellChanges } from '@/lib/bellSignal';
import { workspaceRevision } from '@/lib/workspaceAccess';
import { useEventsStore } from '@/stores/events';
import { FakeEventStreamClient } from '@/test/fakeStream';

import { useLiveEvents } from './useLiveEvents';

vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

it('invalidates scoped resources when stream membership authority changes', () => {
  FakeEventStreamClient.reset();
  const load = vi.spyOn(useEventsStore.getState(), 'load').mockResolvedValue();
  const { unmount } = renderHook(() => useLiveEvents());
  const revision = workspaceRevision();
  act(() => {
    FakeEventStreamClient.instances[0]!.emit({ event: 'access.changed', data: '{}', id: null });
  });
  expect(workspaceRevision()).toBe(revision + 1);
  unmount();
  expect(FakeEventStreamClient.instances[0]!.stop).toHaveBeenCalled();
  load.mockRestore();
});

it('resnapshots after each unresumed hello, not on status changes, and cancels on unmount', () => {
  FakeEventStreamClient.reset();
  const load = vi.spyOn(useEventsStore.getState(), 'load').mockResolvedValue();
  const cancel = vi.spyOn(useEventsStore.getState(), 'cancelLoad');
  const { unmount } = renderHook(() => useLiveEvents());
  const client = FakeEventStreamClient.instances[0]!;
  expect(load).toHaveBeenCalledTimes(1);
  act(() => {
    client.setStatus('reconnecting');
    client.setStatus('live');
    client.setStatus('connecting');
  });
  expect(load).toHaveBeenCalledTimes(1);
  act(() => {
    client.connect();
    client.connect();
  });
  expect(load).toHaveBeenCalledTimes(3);
  unmount();
  expect(cancel).toHaveBeenCalledOnce();
});

it('disconnects hidden tabs and takes a fresh authenticated snapshot on return', () => {
  FakeEventStreamClient.reset();
  const load = vi.spyOn(useEventsStore.getState(), 'load').mockResolvedValue();
  const visibility = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible');
  const { unmount } = renderHook(() => useLiveEvents());
  const first = FakeEventStreamClient.instances[0]!;
  act(() => {
    visibility.mockReturnValue('hidden');
    document.dispatchEvent(new Event('visibilitychange'));
  });
  expect(first.stop).toHaveBeenCalledOnce();
  act(() => {
    visibility.mockReturnValue('visible');
    document.dispatchEvent(new Event('visibilitychange'));
  });
  expect(FakeEventStreamClient.instances).toHaveLength(2);
  expect(load).toHaveBeenCalledTimes(2);
  unmount();
  visibility.mockRestore();
  load.mockRestore();
});

it('asks the bell to refetch on a bell change or new alert without passing their content on', () => {
  FakeEventStreamClient.reset();
  const load = vi.spyOn(useEventsStore.getState(), 'load').mockResolvedValue();
  const handle = vi.spyOn(useEventsStore.getState(), 'handleStreamMessage');
  const changed = vi.fn();
  const stop = subscribeBellChanges(changed);
  const { unmount } = renderHook(() => useLiveEvents());
  const client = FakeEventStreamClient.instances[0]!;
  act(() => {
    client.emit({ event: 'bell.changed', data: '{}', id: null });
    client.emit({ event: 'alert', data: '{"title":"private"}', id: null });
  });
  expect(changed).toHaveBeenCalledTimes(2);
  expect(handle).not.toHaveBeenCalled();
  stop();
  unmount();
  handle.mockRestore();
  load.mockRestore();
});
