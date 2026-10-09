import { act, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useEventsStore } from '@/stores/events';
import { useAuthStore } from '@/stores/auth';
import { installDialogStub } from '@/test/dialogStub';
import { useGlobeStore } from '@/stores/globe';
import { mockWebGl2, resetVisibility, setVisibility } from '@/test/env';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeMap } from '@/test/fakeMap';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { openMapTool } from '@/test/mapTools';
import { renderApp } from '@/test/render';
// Load the real route before rendering it, so the lazy import is not on the clock.
import './GlobePage';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));
installDialogStub();

function layerIds(): string[] {
  const layers = MapboxOverlay.instances.at(-1)?.props.layers as { id: string }[] | undefined;
  return (layers ?? []).map((layer) => layer.id);
}

async function mount() {
  const view = renderApp('/', 'user');
  await screen.findByText('Natural hazards: 1 loaded');
  await waitFor(() => expect(layerIds()).toContain('events-disaster'));
  return view;
}

describe('globe page composition lifecycle', () => {
  beforeEach(() => {
    useEventsStore.setState({ hidden: [] });
    useGlobeStore.setState({ terminator: true, opsRoom: false, mode: 'globe' });
    FakeMap.reset();
    MapboxOverlay.reset();
    FakeEventStreamClient.reset();
    mockWebGl2(true);
  });
  afterEach(() => {
    resetVisibility();
  });

  it('closes the stream and private workspace immediately when the idle session expires', async () => {
    const { router } = await mount();
    const stream = FakeEventStreamClient.instances[0]!;
    const map = FakeMap.instances[0]!;
    act(() => {
      void useAuthStore.getState().expireIdleSession();
    });
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(stream.stop).toHaveBeenCalledOnce();
    expect(map.remove).toHaveBeenCalledOnce();
    expect(useAuthStore.getState().accessToken).toBeNull();
    await useAuthStore.getState().pendingLogout;
  });

  it('keeps one engine, overlay and stream through panel, selection and preference changes', async () => {
    const { user, router } = await mount();
    const map = FakeMap.instances[0]!;
    const stream = FakeEventStreamClient.instances[0]!;

    await openMapTool(user, 'Map style');
    expect(router.state.location.search).toContain('panel=');
    act(() => useEventsStore.getState().select('e1'));
    act(() => useGlobeStore.getState().toggleTerminator());
    act(() => useEventsStore.getState().toggleCategory('news'));
    act(() => useGlobeStore.getState().setMode('map'));

    expect(FakeMap.instances).toEqual([map]);
    expect(MapboxOverlay.instances).toHaveLength(1);
    expect(FakeEventStreamClient.instances).toEqual([stream]);
    expect(stream.start).toHaveBeenCalledOnce();
    expect(stream.stop).not.toHaveBeenCalled();
    expect(map.remove).not.toHaveBeenCalled();
    expect(layerIds()).toContain('events-disaster');
    expect(layerIds()).not.toContain('terminator');
  });

  it('pauses the stream while hidden, restores the scene and cleans up once on unmount', async () => {
    const { unmount } = await mount();
    const map = FakeMap.instances[0]!;
    const first = FakeEventStreamClient.instances[0]!;

    act(() => setVisibility('hidden'));
    expect(first.stop).toHaveBeenCalledOnce();
    act(() => setVisibility('visible'));
    expect(FakeEventStreamClient.instances).toHaveLength(2);
    const second = FakeEventStreamClient.instances[1]!;
    expect(second.start).toHaveBeenCalledOnce();
    expect(first.stop).toHaveBeenCalledOnce();
    // The mirror and engine survive the pause, so the scene is redrawn without a new map.
    expect(FakeMap.instances).toEqual([map]);
    expect(layerIds()).toEqual(expect.arrayContaining(['events-disaster', 'terminator']));

    unmount();
    expect(second.stop).toHaveBeenCalledOnce();
    expect(first.stop).toHaveBeenCalledOnce();
    expect(map.remove).toHaveBeenCalledOnce();
    expect(MapboxOverlay.instances[0]!.finalize).toHaveBeenCalledOnce();
    expect(useEventsStore.getState().coverageBounds).toBeNull();
  });
});
