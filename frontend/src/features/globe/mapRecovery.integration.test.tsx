import { ScatterplotLayer } from '@deck.gl/layers';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { useEffect, useRef } from 'react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import { useGlobeEngine } from './useGlobeEngine';
import { MapCanvas } from './MapCanvas';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
beforeEach(() => {
  FakeMap.reset();
  MapboxOverlay.reset();
  vi.useFakeTimers();
});
afterEach(() => vi.useRealTimers());

function Harness() {
  const container = useRef<HTMLDivElement>(null);
  const engine = useGlobeEngine(container, { enabled: true, mode: 'map', baseLayer: 'hybrid' });
  const { setLayers } = engine;
  useEffect(() => {
    setLayers([new ScatterplotLayer({ id: 'latest-scene' })]);
  }, [setLayers]);
  return <MapCanvas containerRef={container} supported mode="map" engine={engine} />;
}

it('shows graphics recovery status and restores camera and scene only after manual reload', () => {
  render(<Harness />);
  const map = FakeMap.instances[0]!;
  map.getBearing.mockReturnValue(123);
  act(() => map.fire('webglcontextlost'));
  expect(screen.getByRole('status', { name: 'Map graphics status' })).toHaveTextContent('Waiting');
  expect(screen.queryByRole('button', { name: 'Reload map' })).not.toBeInTheDocument();
  act(() => {
    vi.advanceTimersByTime(10_000);
  });
  expect(FakeMap.instances).toHaveLength(1);
  fireEvent.click(screen.getByRole('button', { name: 'Reload map' }));
  expect(FakeMap.instances).toHaveLength(2);
  expect(map.remove).toHaveBeenCalledOnce();
  const restored = FakeMap.instances[1]!;
  expect(restored.jumpTo).toHaveBeenCalledWith({
    center: [10, 30],
    zoom: 1.5,
    bearing: 123,
    pitch: 0,
  });
  expect(MapboxOverlay.instances[1]!.setProps).toHaveBeenCalledWith({
    layers: [expect.objectContaining({ id: 'latest-scene' })],
  });
  expect(screen.queryByRole('status', { name: 'Map graphics status' })).not.toBeInTheDocument();
});

it('does not recreate graphics or schedule work after the view unmounts', () => {
  const { unmount } = render(<Harness />);
  const overlay = MapboxOverlay.instances[0]!;
  act(() => {
    overlay.canvas.dispatchEvent(new Event('webglcontextlost'));
  });
  unmount();
  act(() => (overlay.props.onError as () => void)());
  vi.runAllTimers();
  expect(FakeMap.instances).toHaveLength(1);
  expect(MapboxOverlay.instances).toHaveLength(1);
  expect(vi.getTimerCount()).toBe(0);
});
