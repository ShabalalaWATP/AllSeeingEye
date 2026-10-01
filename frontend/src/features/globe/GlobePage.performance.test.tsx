import { act, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';
import { mockMatchMedia, mockWebGl2, setVisibility } from '@/test/env';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeMap } from '@/test/fakeMap';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { liveEvent } from '@/test/fixtures';
import { openMapTool } from '@/test/mapTools';
import { renderApp } from '@/test/render';
// Load the real route after Vitest hoists its mocks, outside timed layer assertions.
import './GlobePage';

const clock = vi.hoisted(() => ({ now: Date.UTC(2026, 8, 6) }));
vi.mock('@/lib/hooks/useNow', () => ({ useNow: () => clock.now }));
vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

// Count renders of representative stable controls. A memoised export stays memoised with its
// own comparison, so the count reflects what the page really commits.
const { renders, counted } = vi.hoisted(() => {
  const renders = new Map<string, number>();
  async function counted(actual: Record<string, unknown>, name: string) {
    const React = await import('react');
    type Props = Record<string, unknown>;
    const original = actual[name] as
      | React.FunctionComponent<Props>
      | {
          $$typeof: symbol;
          type: React.FunctionComponent<Props>;
          compare?: ((a: Props, b: Props) => boolean) | null;
        };
    const memoised = '$$typeof' in original && original.$$typeof === Symbol.for('react.memo');
    const inner = memoised ? original.type : (original as React.FunctionComponent<Props>);
    function Counted(props: Props) {
      renders.set(name, (renders.get(name) ?? 0) + 1);
      return React.createElement(inner, props);
    }
    return {
      ...actual,
      [name]: memoised ? React.memo(Counted, original.compare ?? undefined) : Counted,
    };
  }
  return { renders, counted };
});
vi.mock('./ModeToolbar', async (load) => counted(await load(), 'ModeToolbar'));
vi.mock('./MapCanvas', async (load) => counted(await load(), 'MapCanvas'));
vi.mock('./MapNavigationTools', async (load) => counted(await load(), 'MapNavigationTools'));
vi.mock('./WorldClocks', async (load) => counted(await load(), 'WorldClocks'));
vi.mock('./GlobeHeading', async (load) => counted(await load(), 'GlobeHeading'));
vi.mock('./MapDisplaySettings', async (load) => counted(await load(), 'MapDisplaySettings'));
vi.mock('./BaseLayerToolbar', async (load) => counted(await load(), 'BaseLayerToolbar'));

interface TestLayer {
  id: string;
  props: {
    onClick: (info: { object: { lon: number; lat: number } }) => void;
    data: { id: string }[];
  };
}

function layer(id: string): TestLayer | undefined {
  return (MapboxOverlay.instances[0]!.props.layers as TestLayer[]).find((item) => item.id === id);
}

async function mount() {
  const view = renderApp('/', 'user');
  await screen.findByText('Natural hazards: 1 loaded');
  await waitFor(() => expect(layer('events-disaster')).toBeDefined());
  return view;
}

describe('globe rendering and motion', () => {
  beforeEach(() => {
    useEventsStore.setState({ hidden: [] });
    useGlobeStore.setState({ terminator: true });
    FakeMap.reset();
    MapboxOverlay.reset();
    FakeEventStreamClient.reset();
    clock.now = Date.UTC(2026, 8, 6);
    useGlobeStore.setState({ opsRoom: false });
    mockWebGl2(true);
  });

  it('keeps event layers stable within a clustering bucket and across clock ticks', async () => {
    await mount();
    const map = FakeMap.instances[0]!;
    const zoom = vi.spyOn(map, 'getZoom');
    const overlay = MapboxOverlay.instances[0]!;
    const original = layer('events-disaster');
    const changes = overlay.setProps.mock.calls.length;
    zoom.mockReturnValue(2.4);
    act(() => map.fire('move'));
    expect(overlay.setProps).toHaveBeenCalledTimes(changes);
    expect(layer('events-disaster')).toBe(original);

    const night = layer('terminator');
    clock.now += 30_000;
    // The fake stream connects on mount. Change status to render the injected clock.
    act(() => useEventsStore.getState().setStatus('reconnecting'));
    expect(layer('terminator')).not.toBe(night);
    expect(layer('events-disaster')).toBe(original);

    zoom.mockReturnValue(2.6);
    act(() => map.fire('move'));
    expect(layer('events-disaster')).not.toBe(original);
    zoom.mockReturnValue(3);
    act(() => map.fire('move'));
    const unclustered = layer('events-disaster');
    zoom.mockReturnValue(8);
    act(() => map.fire('move'));
    expect(layer('events-disaster')).toBe(unclustered);

    act(() => useEventsStore.getState().select('e1'));
    expect(layer('events-disaster')).not.toBe(unclustered);
    const selected = layer('events-disaster');
    act(() => useEventsStore.getState().applyUpsert([liveEvent({ title_en: 'Translated' })]));
    expect(layer('events-disaster')).not.toBe(selected);

    act(() => {
      useEventsStore.getState().applyUpsert([liveEvent({ country_iso: 'UA' })]);
      useEventsStore.getState().setCountry('UA');
    });
    const scoped = layer('events-disaster');
    clock.now += 30_000;
    act(() => useEventsStore.getState().setStatus('offline'));
    expect(layer('events-disaster')).toBe(scoped);
  });

  it('commits no stable-control renders for an event batch, while event views update', async () => {
    const { user } = await mount();
    await openMapTool(user, 'Map style');
    expect(renders.get('MapDisplaySettings')).toBeGreaterThan(0);
    renders.clear();
    act(() => {
      useEventsStore
        .getState()
        .applyBatch(['e2'], [liveEvent({ id: 'fresh', point: { lon: 20, lat: 40 } })]);
    });
    expect(screen.getByText('Natural hazards: 2 loaded')).toBeInTheDocument();
    expect(layer('events-disaster')!.props.data.map((event) => event.id)).toContain('fresh');
    expect(Object.fromEntries(renders)).toEqual({});

    // Relevant inputs still reach the stable controls.
    act(() => useGlobeStore.getState().toggleTerminator());
    expect(renders.get('MapDisplaySettings')).toBe(1);
    expect(renders.get('ModeToolbar')).toBeUndefined();
  });

  it('still updates a time-filtered layer when an event leaves the selected window', async () => {
    await mount();
    act(() => {
      useEventsStore
        .getState()
        .applyUpsert([
          liveEvent({ id: 'old', published_at: new Date(clock.now - 3_590_000).toISOString() }),
          liveEvent({ id: 'fresh', published_at: new Date(clock.now).toISOString() }),
        ]);
      useEventsStore.getState().setWindow(1);
    });
    expect(layer('events-disaster')!.props.data.map((event) => event.id)).toEqual(['fresh', 'old']);
    clock.now += 30_000;
    act(() => useEventsStore.getState().setStatus('reconnecting'));
    expect(layer('events-disaster')!.props.data.map((event) => event.id)).toEqual(['fresh']);
  });

  it('uses the actual zoom when focusing a cluster within a stable grouping', async () => {
    await mount();
    act(() => {
      useEventsStore
        .getState()
        .applyUpsert(
          ['a', 'b', 'c'].map((id) =>
            liveEvent({ id, category: 'news', point: { lon: 1, lat: 1 } }),
          ),
        );
    });
    const map = FakeMap.instances[0]!;
    const zoom = vi.spyOn(map, 'getZoom');
    zoom.mockReturnValue(0.8);
    act(() => map.fire('move'));
    const clustered = layer('clusters');
    zoom.mockReturnValue(1.2);
    act(() => map.fire('move'));
    expect(layer('clusters')).toBe(clustered);
    act(() => clustered!.props.onClick({ object: { lon: 1, lat: 1 } }));
    expect(map.flyTo).toHaveBeenLastCalledWith({ center: [1, 1], zoom: 3.7 });
  });

  it('keeps ops-room motion off when reduced motion is already enabled', async () => {
    mockMatchMedia(true);
    const { user } = await mount();
    await user.keyboard('o');
    expect(useGlobeStore.getState().opsRoom).toBe(true);
    expect(FakeMap.instances[0]!.easeTo).not.toHaveBeenCalled();
  });

  it('pauses on visibility and motion changes, and resumes only when allowed', async () => {
    const media = Object.assign(new EventTarget(), { matches: false });
    vi.spyOn(window, 'matchMedia').mockReturnValue(media as unknown as MediaQueryList);
    const { user } = await mount();
    const map = FakeMap.instances[0]!;
    await user.keyboard('o');
    expect(map.easeTo).toHaveBeenCalledTimes(1);
    act(() => setVisibility('hidden'));
    expect(map.stop).toHaveBeenCalled();
    map.fire('moveend');
    expect(map.easeTo).toHaveBeenCalledTimes(1);
    act(() => setVisibility('visible'));
    expect(map.easeTo).toHaveBeenCalledTimes(2);

    act(() => {
      media.matches = true;
      media.dispatchEvent(new Event('change'));
    });
    map.fire('moveend');
    expect(map.easeTo).toHaveBeenCalledTimes(2);
    act(() => {
      media.matches = false;
      media.dispatchEvent(new Event('change'));
    });
    expect(map.easeTo).toHaveBeenCalledTimes(3);
    await user.keyboard('{Escape}');
  });
});
