import { act, renderHook } from '@testing-library/react';
import { expect, it, vi } from 'vitest';

import type { LiveEvent } from '@/lib/api/eventSchemas';
import { liveEvent } from '@/test/fixtures';

import type { GlobeEngineHandle } from './useGlobeEngine';
import type { GlobeEvents } from './useGlobeEvents';
import { useGlobeSelection } from './useGlobeSelection';

function setup(picking = false, hidden: string[] = []) {
  const ship = liveEvent({ id: 'ship', category: 'maritime', point: { lon: 4, lat: 50 } });
  const quake = liveEvent({ id: 'quake', point: { lon: 10, lat: 20 } });
  const data = {
    hidden,
    renderHidden: hidden,
    quality: { filtered: [ship, quake] },
    select: vi.fn(),
    setCountry: vi.fn(),
    toggleCategory: vi.fn(),
    observations: { visibility: { aircraft: true, vessels: false }, toggle: vi.fn() },
  };
  const engine = { flyTo: vi.fn(), getZoom: () => 2 } as unknown as GlobeEngineHandle;
  const sources = { context: { choose: vi.fn() }, closeCatalogues: vi.fn() };
  const countryByIso = {
    UA: { iso: 'UA', name: 'Ukraine', centroid: [31, 49], bounds: [22, 44, 40, 52] },
  };
  const view = renderHook(() =>
    useGlobeSelection({
      data: data as unknown as GlobeEvents,
      sources: sources as never,
      engine,
      picking,
      countryByIso: countryByIso as never,
    }),
  );
  return { ...view, data, engine, sources, ship, quake };
}

it('closes catalogue inspection before choosing an event, and while picking ignores picks', () => {
  const { result, data, sources, quake } = setup();
  act(() => result.current.choose(quake));
  expect(sources.closeCatalogues).toHaveBeenCalledOnce();
  expect(data.select).toHaveBeenLastCalledWith('quake');
  expect(result.current.pickableEvents.map((event: LiveEvent) => event.id)).toEqual([
    'ship',
    'quake',
  ]);

  const tool = setup(true);
  act(() => tool.result.current.choose(tool.quake));
  act(() => tool.result.current.onPick(tool.quake));
  expect(tool.data.select).not.toHaveBeenCalled();
  expect(tool.sources.closeCatalogues).not.toHaveBeenCalled();
});

it('enables a hidden overlay and category before focusing listed traffic', () => {
  const { result, data, engine, ship } = setup(false, ['maritime']);
  act(() => result.current.selectTraffic(ship));
  expect(data.observations.toggle).toHaveBeenCalledWith('vessels');
  expect(data.toggleCategory).toHaveBeenCalledWith('maritime');
  expect(data.select).toHaveBeenLastCalledWith('ship');
  expect(engine.flyTo).toHaveBeenLastCalledWith({ center: [4, 50], zoom: 5 });
});

it('routes context picks to the context owner and nations to the event scope', () => {
  const { result, data, engine, sources, quake } = setup();
  act(() => result.current.selectContext(quake));
  expect(sources.context.choose).toHaveBeenCalledWith(quake);
  expect(data.select).toHaveBeenLastCalledWith(null);
  act(() => result.current.changeNation('UA'));
  expect(data.setCountry).toHaveBeenCalledWith('UA');
  expect(engine.flyTo).toHaveBeenLastCalledWith(expect.objectContaining({ center: [31, 49] }));
  act(() => result.current.focus(quake));
  expect(data.select).toHaveBeenLastCalledWith('quake');
});

it('opens a cluster without a selected event and highlights overlapping picks', () => {
  const { result, data } = setup();
  act(() =>
    result.current.onCluster({
      id: 'c1',
      category: 'disaster',
      lon: 1,
      lat: 1,
      count: 2,
      maxSeverity: 0,
      members: [],
    }),
  );
  expect(data.select).toHaveBeenLastCalledWith(null);
  expect(result.current.details?.kind).toBe('cluster');
  expect(result.current.highlightedId).toBeNull();
});
