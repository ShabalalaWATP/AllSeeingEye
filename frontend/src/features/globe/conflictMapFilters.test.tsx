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
    { id: string; props: { data: { id: string; category: string }[] } }[] | undefined;
  return (
    layers
      ?.find((layer) => layer.id === 'event-icons')
      ?.props.data.filter((event) => event.category === 'conflict')
      .map((event) => event.id) ?? []
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
    await user.click(screen.getByRole('button', { name: 'Report filters' }));
    await user.click(screen.getByRole('radio', { name: /Protests \/ demonstrations/ }));
    await waitFor(() => expect(conflictIds()).toEqual(['protest']));
    expect(useEventsStore.getState().selectedId).toBeNull();
    await user.click(screen.getByRole('switch', { name: /Conflict.*unrest/ }));
    await waitFor(() => expect(conflictIds()).toEqual([]));
  },
);

it.each(['globe', 'map'] as const)(
  'requires an explicit opt-in for unreviewed media markers in %s and removes rejected updates',
  async (mode) => {
    useGlobeStore.setState({ mode });
    const { user } = renderApp('/', 'user');
    await waitFor(() => expect(useEventsStore.getState().loaded).toBe(true));
    const signal = liveEvent({
      id: 'raw-signal',
      source_id: 'gdelt_events',
      category: 'conflict',
      subtype: 'fight',
      point: { lon: 20, lat: 10 },
    });
    act(() => useEventsStore.getState().applyUpsert([signal]));
    expect(conflictIds()).not.toContain('raw-signal');
    await user.click(screen.getByRole('button', { name: 'Conflict report filters' }));
    await user.click(screen.getByRole('button', { name: 'Report filters' }));
    const toggle = screen.getByRole('checkbox', { name: 'Unreviewed media signals (1 loaded)' });
    expect(toggle).not.toBeChecked();
    await user.click(toggle);
    await waitFor(() => expect(conflictIds()).toContain('raw-signal'));
    act(() => useEventsStore.getState().select('raw-signal'));
    expect(screen.getByText('Unreviewed media signal')).toBeVisible();
    act(() =>
      useEventsStore.getState().applyUpsert([
        liveEvent({
          ...signal,
          attributes: {
            conflict_screening: 'llm',
            conflict_relevance: 'unrelated',
            conflict_screening_reason: 'A construction accident, not armed conflict.',
          },
        }),
      ]),
    );
    await waitFor(() => expect(conflictIds()).not.toContain('raw-signal'));
    expect(useEventsStore.getState().selectedId).toBeNull();
    expect(screen.queryByRole('complementary', { name: 'Event details' })).not.toBeInTheDocument();
  },
);
