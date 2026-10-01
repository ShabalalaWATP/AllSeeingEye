import { renderHook } from '@testing-library/react';
import { ScatterplotLayer } from '@deck.gl/layers';
import { beforeEach, expect, it, vi } from 'vitest';

import type { GlobeEngineHandle } from './useGlobeEngine';
import type { GlobeEvents } from './useGlobeEvents';
import type { GlobeSources } from './useGlobeSources';
import { useGlobeCatalogueLayers } from './useGlobeCatalogueLayers';

const seen = vi.hoisted(() => ({
  closers: [] as unknown[],
  enabled: new Map<string, unknown>(),
}));
const layers = vi.hoisted(() => (id: string) => [{ id }]);
vi.mock('./useNewsCountryLayers', () => ({
  useNewsCountryLayers: (_n: unknown, _e: unknown, _g: unknown, close: unknown) => {
    seen.closers.push(close);
    return layers('news');
  },
}));
vi.mock('./useCyberMapSelection', () => ({
  useCyberMapSelection: (options: { closeOthers: unknown; enabled: boolean }) => {
    seen.closers.push(options.closeOthers);
    seen.enabled.set('cyber', options.enabled);
    return { layers: layers('cyber'), selectRecord: vi.fn() };
  },
}));
vi.mock('./useNetworkMap', () => ({
  useNetworkMapSelection: (options: { closeOthers: unknown; selectContext: unknown }) => {
    seen.closers.push(options.closeOthers);
    seen.enabled.set('networkContext', options.selectContext);
    return { layers: layers('network'), selectRecord: vi.fn() };
  },
}));
vi.mock('./useRadarAttackMap', () => ({
  useRadarAttackLayers: (options: { closeOthers: unknown }) => {
    seen.closers.push(options.closeOthers);
    return layers('radar');
  },
}));
vi.mock('./useConflictRegionSelection', () => ({
  useConflictRegionSelection: (_r: unknown, enabled: boolean, _p: unknown, close: unknown) => {
    seen.closers.push(close);
    seen.enabled.set('regions', enabled);
    return { layers: layers('regions'), focus: vi.fn() };
  },
}));
vi.mock('./cameras/useCameraSelection', () => ({
  useCameraSelection: (_c: unknown, _p: unknown, close: unknown) => {
    seen.closers.push(close);
    return { cameraLayers: layers('cameras'), focusCamera: vi.fn() };
  },
}));
vi.mock('./figures/useFigureSelection', () => ({
  useFigureSelection: (_f: unknown, _p: unknown, close: unknown) => {
    seen.closers.push(close);
    return { figureLayers: layers('figures'), focusFigure: vi.fn() };
  },
}));
vi.mock('./infrastructure/useInfrastructureSelection', () => ({
  useInfrastructureSelection: (_i: unknown, _p: unknown, close: unknown) => {
    seen.closers.push(close);
    return { layers: layers('infrastructure'), focus: vi.fn() };
  },
}));

beforeEach(() => {
  seen.closers = [];
  seen.enabled.clear();
});

function render(hidden: string[]) {
  const close = vi.fn();
  const selectContext = vi.fn();
  const view = renderHook(() =>
    useGlobeCatalogueLayers({
      data: {
        hidden,
        quality: { filter: 'all' },
        windowHours: null,
      } as unknown as GlobeEvents,
      sources: {
        network: { open: false },
        context: { event: null, layers: layers('context') },
      } as unknown as GlobeSources,
      selection: { close, selectContext },
      engine: {} as GlobeEngineHandle,
      picking: false,
      symbolMode: 'globe',
      countryByIso: {},
      gridLayers: [new ScatterplotLayer({ id: 'grid' })],
      toolLayers: [new ScatterplotLayer({ id: 'tools' })],
      now: 0,
    }),
  );
  return { ...view, close, selectContext };
}

it('draws catalogues in the established order around the event layers', () => {
  const { result } = render([]);
  expect(
    result.current.layerGroups.map((group) =>
      group === 'events' ? group : group.map((layer) => layer.id).join(),
    ),
  ).toEqual([
    'grid',
    'infrastructure',
    'events',
    'regions',
    'cameras',
    'figures',
    'context',
    'cyber',
    'radar',
    'network',
    'news',
    'tools',
  ]);
});

it('closes event inspection before any catalogue selection and follows category visibility', () => {
  const { close, selectContext } = render(['cyber', 'conflict']);
  expect(seen.closers).toHaveLength(8);
  expect(new Set(seen.closers)).toEqual(new Set([close]));
  expect(Object.fromEntries(seen.enabled)).toEqual({
    cyber: false,
    regions: false,
    networkContext: selectContext,
  });
});
