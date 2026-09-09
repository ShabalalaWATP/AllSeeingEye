import { act, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { renderApp } from '@/test/render';
import { mockWebGl2 } from '@/test/env';
import { liveEvent } from '@/test/fixtures';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

// Resolve the lazy route before timed UI assertions, including on a cold test worker.
import './GlobePage';

beforeEach(() => {
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
});

function conflictIds() {
  const layers = MapboxOverlay.instances[0]?.props.layers as
    { id: string; props: { data: { id: string }[] } }[] | undefined;
  return (
    layers?.find((layer) => layer.id === 'events-conflict')?.props.data.map((event) => event.id) ??
    []
  );
}

it.each(['globe', 'map'] as const)(
  'filters the %s markers and clears excluded selection while retaining the master switch',
  async (mode) => {
    useGlobeStore.setState({ mode });
    const { user } = renderApp('/', 'user');
    await waitFor(() => expect(useEventsStore.getState().loaded).toBe(true));
    act(() => {
      useEventsStore.getState().applyUpsert([
        liveEvent({
          id: 'fight',
          category: 'conflict',
          subtype: 'fight',
          point: { lon: 20, lat: 10 },
        }),
        liveEvent({
          id: 'protest',
          category: 'conflict',
          subtype: 'protest',
          point: { lon: 50, lat: 20 },
        }),
      ]);
      useEventsStore.getState().select('fight');
    });
    await waitFor(() =>
      expect(conflictIds()).toEqual(expect.arrayContaining(['fight', 'protest'])),
    );
    await user.click(screen.getByRole('button', { name: 'Conflict report filters' }));
    await user.click(screen.getByRole('radio', { name: /Protests and riots/ }));
    await waitFor(() => expect(conflictIds()).toEqual(['protest']));
    expect(useEventsStore.getState().selectedId).toBeNull();
    await user.click(screen.getByRole('switch', { name: /Conflict.*unrest/ }));
    await waitFor(() => expect(conflictIds()).toEqual([]));
  },
);
