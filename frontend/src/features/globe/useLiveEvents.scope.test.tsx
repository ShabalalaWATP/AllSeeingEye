import { act, renderHook } from '@testing-library/react';
import { expect, it, vi } from 'vitest';

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
