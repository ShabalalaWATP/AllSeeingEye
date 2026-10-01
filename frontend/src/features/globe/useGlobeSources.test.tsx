import { renderHook } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';

import type { GlobeEvents } from './useGlobeEvents';
import { useGlobeSources } from './useGlobeSources';

const calls = vi.hoisted(() => ({
  closed: [] as string[],
  radar: [] as boolean[],
  regions: [] as boolean[],
  context: [] as unknown[][],
  guarded: 0,
}));
const source = (name: string) => ({ close: () => calls.closed.push(name) });
vi.mock('./useNetworkMap', () => ({ useNetworkMap: () => source('network') }));
vi.mock('./useRadarAttackMap', () => ({
  useRadarAttackMap: (enabled: boolean) => {
    calls.radar.push(enabled);
    return source('radar');
  },
}));
vi.mock('./useConflictRegions', () => ({
  useConflictRegions: (enabled: boolean) => {
    calls.regions.push(enabled);
    return source('regions');
  },
}));
vi.mock('./useReportingReferences', () => ({
  useReportingReferences: () => ({ cyber: source('cyber'), news: source('news') }),
}));
vi.mock('./cameras/useCameras', () => ({ useCameras: () => source('cameras') }));
vi.mock('./figures/useFigures', () => ({ useFigures: () => source('figures') }));
vi.mock('./infrastructure/useInfrastructure', () => ({
  useInfrastructure: () => source('infrastructure'),
}));
vi.mock('./context/useContextSelection', () => ({
  useContextSelection: (...args: unknown[]) => {
    calls.context.push(args);
    return source('context');
  },
}));
vi.mock('./useNewsSelectionGuard', () => ({
  useNewsSelectionGuard: () => {
    calls.guarded += 1;
  },
}));

function scope(hidden: string[], supported = true) {
  return {
    data: { hidden, country: 'UA' } as unknown as GlobeEvents,
    countryByIso: {},
    supported,
    visible: true,
    picking: true,
    symbolMode: 'map' as const,
    now: 0,
  };
}

beforeEach(() => {
  calls.closed = [];
  calls.radar = [];
  calls.regions = [];
  calls.context = [];
  calls.guarded = 0;
});

it('closes every catalogue inspector through one action', () => {
  const { result, rerender } = renderHook(() => useGlobeSources(scope([])));
  const close = result.current.closeCatalogues;
  close();
  expect(calls.closed.sort()).toEqual(
    [
      'cameras',
      'context',
      'cyber',
      'figures',
      'infrastructure',
      'network',
      'news',
      'radar',
      'regions',
    ].sort(),
  );
  rerender();
  expect(calls.guarded).toBe(2);
});

it('ties cyber and conflict sources to their category visibility', () => {
  const { rerender } = renderHook((props) => useGlobeSources(props), {
    initialProps: scope([]),
  });
  rerender(scope(['cyber', 'conflict']));
  rerender(scope([], false));
  expect(calls.radar).toEqual([true, false, true]);
  expect(calls.regions).toEqual([true, false, false]);
  expect(calls.context[0]).toEqual(['UA', true, 'map']);
});
