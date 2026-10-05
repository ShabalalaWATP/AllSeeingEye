import { act, renderHook, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { LiveEvent } from '@/lib/api/eventSchemas';
import { workspaceRevision } from '@/lib/workspaceAccess';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';
import { usePlanMapFilterStore } from '@/stores/planMapFilter';
import { mockWebGl2 } from '@/test/env';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeMap } from '@/test/fakeMap';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { liveEvent, plan } from '@/test/fixtures';
import { openMapTool } from '@/test/mapTools';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { useDailyImageryStore } from './imagery/dailyImageryStore';
import { useGlobeEventScope } from './GlobeEventScope';
import './GlobePage';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

// Keep the real hooks and panel behaviour. Count composition work, not wall-clock time.
const calls = vi.hoisted(() => ({ canvas: 0, style: 0 }));
vi.mock('./useGlobeCanvas', async (load) => {
  const actual = await load<typeof import('./useGlobeCanvas')>();
  return {
    ...actual,
    useGlobeCanvas: (...args: Parameters<typeof actual.useGlobeCanvas>) => {
      calls.canvas += 1;
      return actual.useGlobeCanvas(...args);
    },
  };
});
vi.mock('./imagery/DailyImageryControls', async (load) => {
  const actual = await load<typeof import('./imagery/DailyImageryControls')>();
  return {
    ...actual,
    DailyImageryControls: function CountedDailyImageryControls() {
      calls.style += 1;
      return <actual.DailyImageryControls />;
    },
  };
});

interface DataLayer {
  id: string;
  props: { data: LiveEvent[] };
}

function disasterRows() {
  const layers = MapboxOverlay.instances[0]?.props.layers as DataLayer[] | undefined;
  return layers?.find((item) => item.id === 'events-disaster')?.props.data ?? [];
}

async function mount() {
  const view = renderApp('/', 'user');
  await screen.findByText('Natural hazards: 1 loaded');
  await waitFor(() => expect(disasterRows()).toHaveLength(1));
  return view;
}

describe('globe event subscription boundary', () => {
  beforeEach(() => {
    useEventsStore.setState({ hidden: [] });
    useGlobeStore.setState({ mode: 'globe', terminator: false, opsRoom: false });
    useDailyImageryStore.getState().reset();
    usePlanMapFilterStore.getState().reset();
    FakeMap.reset();
    MapboxOverlay.reset();
    FakeEventStreamClient.reset();
    calls.canvas = 0;
    calls.style = 0;
    mockWebGl2(true);
  });
  afterEach(() => {
    useDailyImageryStore.getState().reset();
    usePlanMapFilterStore.getState().reset();
  });

  it('requires the authoritative scope for event consumers', () => {
    expect(() => renderHook(() => useGlobeEventScope())).toThrow(
      'Globe event views require GlobeEventScope.',
    );
  });

  it('updates batch counts, layers and current selected details without recomposing the shell', async () => {
    const { unmount } = await mount();
    const original = liveEvent({ id: 'current', title: 'Original observation' });
    act(() => {
      useEventsStore.getState().applyUpsert([original]);
      useEventsStore.getState().select(original.id);
    });
    expect(screen.getByRole('heading', { name: original.title })).toBeVisible();
    const corrected = { ...original, title: 'Corrected observation', point: { lon: 25, lat: 45 } };
    const fresh = liveEvent({ id: 'fresh', point: { lon: 80, lat: 10 } });
    calls.canvas = 0;
    act(() => useEventsStore.getState().applyBatch(['e1'], [corrected, fresh]));

    expect(screen.getByText('Natural hazards: 2 loaded')).toBeInTheDocument();
    expect(disasterRows().find((event) => event.id === corrected.id)).toBe(corrected);
    expect(disasterRows().find((event) => event.id === fresh.id)).toBe(fresh);
    expect(screen.getByRole('heading', { name: corrected.title })).toBeVisible();
    expect(screen.queryByRole('heading', { name: original.title })).not.toBeInTheDocument();
    expect(calls.canvas).toBe(0);

    const stream = FakeEventStreamClient.instances[0]!;
    const map = FakeMap.instances[0]!;
    expect(FakeEventStreamClient.instances).toHaveLength(1);
    expect(stream.start).toHaveBeenCalledOnce();
    expect(FakeMap.instances).toHaveLength(1);
    unmount();
    expect(stream.stop).toHaveBeenCalledOnce();
    expect(map.remove).toHaveBeenCalledOnce();
    expect(MapboxOverlay.instances[0]!.finalize).toHaveBeenCalledOnce();
  });

  it('keeps an open Map style subtree untouched by batches while its controls remain live', async () => {
    const { user, router } = await mount();
    await openMapTool(user, 'Map style');
    expect(calls.style).toBeGreaterThan(0);
    const dayNight = screen.getByRole('switch', { name: 'Day and night' });
    dayNight.focus();
    const search = router.state.location.search;
    calls.style = 0;
    act(() => useEventsStore.getState().applyUpsert([liveEvent({ id: 'new' })]));
    expect(screen.getByText('Natural hazards: 2 loaded')).toBeInTheDocument();
    expect(calls.style).toBe(0);
    expect(dayNight).toHaveFocus();
    expect(router.state.location.search).toBe(search);

    await user.click(dayNight);
    expect(dayNight).toHaveAttribute('aria-checked', 'true');
    expect(useGlobeStore.getState().terminator).toBe(true);
    await user.click(screen.getByRole('switch', { name: 'Daily satellite imagery' }));
    expect(screen.getByRole('switch', { name: 'Daily satellite imagery' })).toHaveAttribute(
      'aria-checked',
      'true',
    );
    await user.click(
      within(screen.getByRole('group', { name: 'View mode' })).getByRole('button', { name: 'Map' }),
    );
    expect(screen.getByRole('region', { name: 'Map' })).toBeInTheDocument();
    expect(FakeEventStreamClient.instances).toHaveLength(1);
    expect(FakeMap.instances).toHaveLength(1);
  });

  it('keeps filter changes and access invalidation active through the same stream', async () => {
    const { unmount } = await mount();
    act(() => useEventsStore.getState().select('e1'));
    expect(screen.getByRole('complementary', { name: 'Event details' })).toBeVisible();
    act(() => useEventsStore.getState().toggleCategory('disaster'));
    expect(disasterRows()).toEqual([]);
    expect(screen.queryByRole('complementary', { name: 'Event details' })).not.toBeInTheDocument();
    expect(useEventsStore.getState().selectedId).toBeNull();
    act(() => useEventsStore.getState().toggleCategory('disaster'));
    expect(disasterRows().map((event) => event.id)).toEqual(['e1']);

    server.use(
      http.get('/api/direction/plans/:id/map-matches', () =>
        HttpResponse.json({
          plan,
          window_hours: 168,
          pool_limit: 5000,
          per_requirement_limit: 30,
          considered: 2,
          truncated: false,
          matches: [{ event_id: 'e1', codes: ['SIR-1.1'] }],
        }),
      ),
    );
    act(() => {
      useEventsStore
        .getState()
        .applyUpsert([liveEvent({ id: 'outside-plan', point: { lon: 90, lat: 10 } })]);
      usePlanMapFilterStore.getState().select(plan.id);
    });
    await waitFor(() => expect(usePlanMapFilterStore.getState().status).toBe('ready'));
    expect(disasterRows().map((event) => event.id)).toEqual(['e1']);

    const stream = FakeEventStreamClient.instances[0]!;
    const revision = workspaceRevision();
    act(() => stream.emit({ event: 'access.changed', data: '{}', id: null }));
    expect(workspaceRevision()).toBe(revision + 1);
    expect(usePlanMapFilterStore.getState()).toMatchObject({
      planId: null,
      codes: null,
      result: null,
    });
    expect(
      disasterRows()
        .map((event) => event.id)
        .sort(),
    ).toEqual(['e1', 'outside-plan']);
    expect(FakeEventStreamClient.instances).toHaveLength(1);
    expect(stream.stop).not.toHaveBeenCalled();
    unmount();
    expect(stream.stop).toHaveBeenCalledOnce();
  });
});
