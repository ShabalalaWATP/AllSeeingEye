import { act, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import type { LiveEvent } from '@/lib/api/eventSchemas';
import { NOW_TICK_MS } from '@/lib/hooks/useNow';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';
import { mockWebGl2 } from '@/test/env';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeMap } from '@/test/fakeMap';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { liveEvent } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import './GlobePage';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

const shell = vi.hoisted(() => ({ renders: 0 }));
vi.mock('./useGlobeCanvas', async (load) => {
  const actual = await load<typeof import('./useGlobeCanvas')>();
  return {
    ...actual,
    useGlobeCanvas: (...args: Parameters<typeof actual.useGlobeCanvas>) => {
      shell.renders += 1;
      return actual.useGlobeCanvas(...args);
    },
  };
});

function disasterRows() {
  const layers = MapboxOverlay.instances[0]?.props.layers as
    { id: string; props: { data: LiveEvent[] } }[] | undefined;
  return layers?.find((item) => item.id === 'events-disaster')?.props.data ?? [];
}

beforeEach(() => {
  // Preserve the real useNow subscription. Only its Date/interval clock is controlled;
  // requests, animation frames, user events and assertion timeouts use their normal timers.
  vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] });
  vi.setSystemTime(Date.UTC(2026, 8, 6));
  useEventsStore.setState({ hidden: [] });
  useGlobeStore.setState({ mode: 'globe', terminator: false, opsRoom: false });
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
});
afterEach(() => vi.useRealTimers());

it('expires the scoped layer and selection on a real clock tick without a stream or shell update', async () => {
  const { unmount } = renderApp('/', 'user');
  await screen.findByText('Natural hazards: 1 loaded');
  await waitFor(() => expect(disasterRows()).toHaveLength(1));
  const old = liveEvent({
    id: 'old',
    title: 'Observation at the time boundary',
    published_at: new Date(Date.now() - 3_590_000).toISOString(),
  });
  const fresh = liveEvent({
    id: 'fresh',
    point: { lon: 90, lat: 10 },
    published_at: new Date(Date.now()).toISOString(),
  });
  act(() => {
    useEventsStore.getState().applyUpsert([old, fresh]);
    useEventsStore.getState().setWindow(1);
    useEventsStore.getState().select(old.id);
  });
  expect(disasterRows()).toEqual([fresh, old]);
  expect(screen.getByRole('heading', { name: old.title })).toBeVisible();
  const mirror = useEventsStore.getState().list;
  const status = useEventsStore.getState().status;
  shell.renders = 0;

  await act(() => vi.advanceTimersByTimeAsync(NOW_TICK_MS));

  expect(disasterRows()).toEqual([fresh]);
  expect(disasterRows()[0]).toBe(fresh);
  expect(screen.getByText('Natural hazards: 1 loaded')).toBeInTheDocument();
  expect(screen.queryByRole('heading', { name: old.title })).not.toBeInTheDocument();
  expect(useEventsStore.getState().selectedId).toBeNull();
  expect(useEventsStore.getState().list).toBe(mirror);
  expect(useEventsStore.getState().status).toBe(status);
  expect(shell.renders).toBe(0);
  expect(FakeEventStreamClient.instances).toHaveLength(1);
  unmount();
  expect(FakeEventStreamClient.instances[0]!.stop).toHaveBeenCalledOnce();
});
