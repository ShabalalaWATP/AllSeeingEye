import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { useTerrainAnalysis } from './useTerrainAnalysis';
import { fetchTerrainElevations, type TerrainElevations } from '@/lib/api/terrain';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import type { TerrainStudyInput } from '@/lib/map/terrainAnalysis';

vi.mock('@/lib/api/terrain', () => ({ fetchTerrainElevations: vi.fn() }));
const fetch = vi.mocked(fetchTerrainElevations);
const input: TerrainStudyInput = {
  mode: 'profile',
  origin: [0, 51],
  end: [0.001, 51],
  observerHeightM: 2,
  radiusKm: 1,
};
function source(count: number): TerrainElevations {
  return {
    elevations_m: Array.from({ length: count }, () => 10),
    zoom: 10,
    resolution_m: 90,
    provider: 'Mapzen Terrain Tiles',
    attribution: 'Fixture',
    attribution_url: 'https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
    limitations: '',
  };
}
beforeEach(() => {
  fetch.mockReset();
});

it('makes no background request and retains results independently of panel state', async () => {
  fetch.mockImplementation((positions) => Promise.resolve(source(positions.length)));
  const { result } = renderHook(useTerrainAnalysis);
  expect(fetch).not.toHaveBeenCalled();
  await act(async () => {
    await result.current.run(input);
  });
  expect(result.current.result?.samples).toHaveLength(3);
  expect(result.current.busy).toBe(false);
  expect(result.current.error).toBeNull();
});

it('clears stale results on failure, rejects invalid studies before the request', async () => {
  fetch.mockRejectedValue(new Error('Terrain unavailable'));
  const { result } = renderHook(useTerrainAnalysis);
  await act(async () => {
    await result.current.run(input);
  });
  expect(result.current.error).toBe('Terrain unavailable');
  expect(result.current.result).toBeNull();
  fetch.mockClear();
  await act(async () => {
    await result.current.run({ ...input, end: [180, 51] });
  });
  expect(result.current.error).toMatch(/200 km/);
  expect(fetch).not.toHaveBeenCalled();
});

it('ignores responses after cancellation even if the transport ignores abort', async () => {
  let resolve!: (value: TerrainElevations) => void;
  fetch.mockImplementation(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  const { result } = renderHook(useTerrainAnalysis);
  let pending!: Promise<void>;
  act(() => {
    pending = result.current.run(input);
  });
  expect(result.current.busy).toBe(true);
  act(() => result.current.clear());
  expect(fetch.mock.calls[0]?.[1].aborted).toBe(true);
  await act(async () => {
    resolve(source(3));
    await pending;
  });
  expect(result.current.result).toBeNull();
  expect(result.current.error).toBeNull();
});

it('clears drafts, result and pending work on workspace authority changes', async () => {
  fetch.mockImplementation((positions) => Promise.resolve(source(positions.length)));
  const { result } = renderHook(useTerrainAnalysis);
  await act(async () => {
    await result.current.run(input);
  });
  act(() => result.current.setDraft({ ...result.current.draft, originLat: '51' }));
  act(() => invalidateWorkspaceAccess());
  await waitFor(() => expect(result.current.result).toBeNull());
  expect(result.current.draft.originLat).toBe('');
});

it('suppresses a late rejected request after a replacement study succeeds', async () => {
  let reject!: (reason: unknown) => void;
  fetch.mockImplementationOnce(
    () =>
      new Promise((_, fail) => {
        reject = fail;
      }),
  );
  fetch.mockImplementation((positions) => Promise.resolve(source(positions.length)));
  const { result } = renderHook(useTerrainAnalysis);
  let first!: Promise<void>;
  act(() => {
    first = result.current.run(input);
  });
  await act(async () => {
    await result.current.run({ ...input, end: [0.002, 51] });
  });
  await act(async () => {
    reject(new Error('Late request failed'));
    await first;
  });
  expect(result.current.result?.input.end).toEqual([0.002, 51]);
  expect(result.current.error).toBeNull();
  expect(result.current.busy).toBe(false);
});

it('provides a useful fallback for a transport rejection without an Error object', async () => {
  fetch.mockRejectedValue('Unavailable');
  const { result } = renderHook(useTerrainAnalysis);
  await act(async () => {
    await result.current.run(input);
  });
  expect(result.current.error).toBe('Terrain analysis failed.');
  expect(result.current.result).toBeNull();
});
