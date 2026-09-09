import { act, renderHook } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import type { RfAnalysis } from '@/lib/map/rfAnalysis';
import { createRfTerrainPath } from '@/lib/map/rfTerrainSampling';
import { analyseRfTerrain } from '@/lib/map/rfTerrainAnalysis';
import { DEFAULT_RF_INPUTS } from '@/lib/map/rfPlanning';
import { rfMapEstimate } from '@/lib/map/rfMap';
import { calculateHfSkywave } from '@/lib/map/hfSkywave';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useMapWorkspaceTools } from './useMapWorkspaceTools';
import type { GlobeEngineHandle } from './useGlobeEngine';

function fakeEngine() {
  const handlers = new Set<(point: { lon: number; lat: number }) => void>();
  return {
    engine: {
      onClick: (callback: (point: { lon: number; lat: number }) => void) => {
        handlers.add(callback);
        return () => {
          handlers.delete(callback);
        };
      },
      setSketchMode: vi.fn(),
    } as unknown as GlobeEngineHandle,
    click: () => handlers.forEach((handler) => handler({ lon: 0.02, lat: 51 })),
  };
}

function terrainAnalysis(): RfAnalysis {
  const plan = createRfTerrainPath([0, 51], [0.01, 51], 3);
  const values = [100, 200, 100];
  return {
    kind: 'terrain',
    plan,
    input: DEFAULT_RF_INPUTS,
    terrain: analyseRfTerrain(DEFAULT_RF_INPUTS, plan, values),
    elevations: {
      elevations_m: values,
      zoom: 10,
      resolution_m: 100,
      provider: 'Mapzen Terrain Tiles',
      attribution: 'Fixture',
      attribution_url: 'https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
      limitations: 'Coarse samples',
    },
  };
}

it.each(['map', 'globe'] as const)(
  'integrates terrain sectors and clears stale results in %s',
  (mode) => {
    const { engine, click } = fakeEngine();
    const { result } = renderHook(() => useMapWorkspaceTools(engine, true, mode));
    const analysis = terrainAnalysis();
    act(() => result.current.rf.setEstimate(rfMapEstimate(DEFAULT_RF_INPUTS, [0, 51], null)));
    act(() => result.current.rf.setAnalysis(analysis));
    expect(result.current.rf.estimate).toBeNull();
    const paths = result.current.layers.find((layer) => layer.id === 'rf-terrain-paths');
    expect(paths?.props.wrapLongitude).toBe(mode === 'map');
    expect(paths?.props.data).toEqual(
      expect.arrayContaining([expect.objectContaining({ status: 'blocked' })]),
    );
    act(() => result.current.rf.setPicking('origin'));
    act(click);
    expect(result.current.rf.analysis).toBeNull();
    expect(result.current.layers.some((layer) => layer.id.startsWith('rf-terrain'))).toBe(false);
  },
);

it('keeps calculated layers stable across unrelated drawing changes and clears on authority changes', () => {
  const { engine, click } = fakeEngine();
  const { result, rerender } = renderHook(
    ({ enabled }) => useMapWorkspaceTools(engine, enabled, 'map'),
    {
      initialProps: { enabled: true },
    },
  );
  act(() => result.current.rf.setAnalysis(terrainAnalysis()));
  const before = result.current.layers.find((layer) => layer.id === 'rf-terrain-paths');
  act(() => result.current.drawing.setPicking(true));
  act(click);
  expect(result.current.layers.find((layer) => layer.id === 'rf-terrain-paths')).toBe(before);
  rerender({ enabled: false });
  expect(result.current.rf.analysis).not.toBeNull();
  act(() => invalidateWorkspaceAccess());
  expect(result.current.rf.analysis).toBeNull();
});

it('replaces terrain with HF skywave, resets on edits and removes all analysis on clear', () => {
  const { engine } = fakeEngine();
  const { result } = renderHook(() => useMapWorkspaceTools(engine, true, 'map'));
  act(() => result.current.rf.setAnalysis(terrainAnalysis()));
  act(() =>
    result.current.rf.setAnalysis({
      kind: 'hf-skywave',
      estimate: {
        origin: [0, 51],
        frequencyMHz: 7,
        scenario: calculateHfSkywave({
          frequencyMHz: 7,
          criticalFrequencyMHz: 5,
          virtualHeightKm: 300,
          minElevationDeg: 10,
          maxElevationDeg: 80,
        }),
      },
    }),
  );
  expect(result.current.layers.some((layer) => layer.id.startsWith('rf-terrain'))).toBe(false);
  expect(result.current.layers.some((layer) => layer.id.includes('skywave'))).toBe(true);
  act(() => result.current.rf.setDraft({ ...result.current.rf.draft, presetId: 'custom' }));
  expect(result.current.rf.analysis).toBeNull();
  act(() => result.current.rf.setAnalysis(terrainAnalysis()));
  act(() => result.current.rf.clearReceiver());
  expect(result.current.rf.analysis).toBeNull();
});
