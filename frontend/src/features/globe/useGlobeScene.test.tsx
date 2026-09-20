import { renderHook } from '@testing-library/react';
import { ScatterplotLayer } from '@deck.gl/layers';
import { beforeEach, expect, it, vi } from 'vitest';
import { buildEventLayers } from './layers/registry';
import { buildJamLayer } from './layers/jamming';
import { buildTerminatorLayer } from './layers/terminator';
import { useGlobeScene } from './useGlobeScene';

vi.mock('./layers/registry', () => ({ buildEventLayers: vi.fn() }));
vi.mock('./layers/jamming', () => ({ buildJamLayer: vi.fn() }));
vi.mock('./layers/terminator', () => ({ buildTerminatorLayer: vi.fn() }));
const event = new ScatterplotLayer({ id: 'events' });
const night = new ScatterplotLayer({ id: 'night' });
const jam = new ScatterplotLayer({ id: 'jam' });

beforeEach(() => {
  vi.mocked(buildEventLayers).mockReturnValue([event]);
  vi.mocked(buildJamLayer).mockReturnValue(jam);
  vi.mocked(buildTerminatorLayer).mockReturnValue(night);
});
function scene(): Parameters<typeof useGlobeScene>[0] {
  return {
    engine: { setLayers: vi.fn(), spin: vi.fn() },
    events: [],
    hidden: [],
    selectedId: null,
    highlightedId: null,
    onPick: vi.fn(),
    onCluster: vi.fn(),
    onJam: vi.fn(),
    jamCells: [],
    layerGroups: [],
    supported: true,
    terminator: true,
    lite: false,
    interference: true,
    opsRoom: false,
    reducedMotion: false,
    visible: true,
    now: 0,
    zoom: 2,
    mode: 'globe',
    symbolMode: 'globe',
  };
}
it('preserves group order around events and can insert a new catalogue without scene changes', () => {
  const grid = new ScatterplotLayer({ id: 'grid' });
  const catalogue = new ScatterplotLayer({ id: 'new-catalogue' });
  const measured = new ScatterplotLayer({ id: 'measurement' });
  const props = scene();
  props.layerGroups = [[grid], 'events', [catalogue], [], [measured]];
  const { rerender } = renderHook(useGlobeScene, { initialProps: props });
  expect(props.engine.setLayers).toHaveBeenLastCalledWith([
    night,
    jam,
    grid,
    event,
    catalogue,
    measured,
  ]);
  rerender(props);
  expect(props.engine.setLayers).toHaveBeenCalledOnce();
  rerender({ ...props, layerGroups: [[grid], 'events', [measured]] });
  expect(props.engine.setLayers).toHaveBeenLastCalledWith([night, jam, grid, event, measured]);
});
it('keeps event picking, cluster callbacks and selected event precedence', () => {
  const props = { ...scene(), selectedId: 'selected', highlightedId: 'highlighted' };
  props.layerGroups = ['events'];
  renderHook(useGlobeScene, { initialProps: props });
  expect(buildEventLayers).toHaveBeenLastCalledWith(
    props.events,
    props.hidden,
    props.onPick,
    'selected',
    {
      zoom: 2,
      onCluster: props.onCluster,
      globe: true,
    },
  );
  expect(buildJamLayer).toHaveBeenLastCalledWith(props.jamCells, props.onJam, null);
});
it('turns off idle spin when visibility changes and avoids touching an unsupported renderer', () => {
  const props = { ...scene(), opsRoom: true };
  const { rerender, unmount } = renderHook(useGlobeScene, { initialProps: props });
  expect(props.engine.spin).toHaveBeenLastCalledWith(true);
  rerender({ ...props, visible: false, lite: true, interference: false });
  expect(props.engine.spin).toHaveBeenLastCalledWith(false);
  expect(props.engine.setLayers).toHaveBeenLastCalledWith([]);
  vi.mocked(props.engine.setLayers).mockClear();
  rerender({ ...props, supported: false });
  expect(props.engine.setLayers).not.toHaveBeenCalled();
  unmount();
  expect(props.engine.spin).toHaveBeenLastCalledWith(false);
});
