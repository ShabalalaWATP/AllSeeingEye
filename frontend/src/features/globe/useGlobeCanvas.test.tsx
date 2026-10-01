import { renderHook } from '@testing-library/react';
import { ScatterplotLayer } from '@deck.gl/layers';
import { beforeEach, expect, it, vi } from 'vitest';

import type { GlobeDisplay } from './useGlobeCanvas';
import { useGlobeCanvas } from './useGlobeCanvas';

const leaf = vi.hoisted(() => ({
  engine: { flyTo: () => undefined },
  supported: true,
  coverage: [] as boolean[],
  tools: [] as boolean[],
  areas: [] as boolean[],
  toolLayers: [] as unknown[],
  areaLayers: [] as unknown[],
}));
vi.mock('./useDashboardEngine', () => ({
  useDashboardEngine: () => ({
    supported: leaf.supported,
    containerRef: { current: null },
    engine: leaf.engine,
  }),
}));
vi.mock('./useBritishGrid', () => ({ useBritishGrid: () => ({ layers: [], enabled: false }) }));
vi.mock('./useViewportCoverage', () => ({
  useViewportCoverage: (_: unknown, enabled: boolean) => leaf.coverage.push(enabled),
}));
vi.mock('./useMapWorkspaceTools', () => ({
  useMapWorkspaceTools: (_: unknown, enabled: boolean) => {
    leaf.tools.push(enabled);
    return { layers: leaf.toolLayers, picking: false };
  },
}));
vi.mock('./useMapRenderView', () => ({
  useMapRenderView: () => ({ zoom: 2, symbolMode: 'globe' }),
}));
vi.mock('./useMapReferenceData', () => ({
  useMapReferenceData: () => ({ countryByIso: {}, countries: [] }),
}));
vi.mock('./useSavedMapArea', () => ({
  useSavedMapArea: (_engine: unknown, _countries: unknown, enabled: boolean) => {
    leaf.areas.push(enabled);
    return { layers: leaf.areaLayers };
  },
}));

const display = {
  mode: 'globe',
  baseLayer: 'hybrid',
  setBaseLayer: () => undefined,
  lite: false,
  opsRoom: false,
} as unknown as GlobeDisplay;

beforeEach(() => {
  leaf.supported = true;
  leaf.coverage = [];
  leaf.tools = [];
  leaf.areas = [];
  leaf.toolLayers = [new ScatterplotLayer({ id: 'measure' })];
  leaf.areaLayers = [new ScatterplotLayer({ id: 'saved-area' })];
});

it('loads viewport coverage only for a visible supported map', () => {
  const { rerender } = renderHook(({ visible }) => useGlobeCanvas(display, visible), {
    initialProps: { visible: true },
  });
  rerender({ visible: false });
  leaf.supported = false;
  rerender({ visible: true });
  expect(leaf.coverage).toEqual([true, false, false]);
});

it('suspends workspace tools in the ops room and saved areas outside the flat map', () => {
  const { rerender } = renderHook((props: GlobeDisplay) => useGlobeCanvas(props, true), {
    initialProps: display,
  });
  rerender({ ...display, opsRoom: true, mode: 'map' });
  expect(leaf.tools).toEqual([true, false]);
  expect(leaf.areas).toEqual([false, true]);
});

it('draws tool layers before the saved area and keeps them stable between renders', () => {
  const { result, rerender } = renderHook(() => useGlobeCanvas(display, true));
  const first = result.current.toolLayers;
  expect(first.map((layer) => layer.id)).toEqual(['measure', 'saved-area']);
  rerender();
  expect(result.current.toolLayers).toBe(first);
  expect(result.current.engine).toBe(leaf.engine);
  leaf.areaLayers = [];
  rerender();
  expect(result.current.toolLayers.map((layer) => layer.id)).toEqual(['measure']);
});
