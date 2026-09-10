import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { Geodesic } from 'geographiclib-geodesic';
import { useRfAnalysis } from './useRfAnalysis';
import { fetchTerrainElevations, type TerrainElevations } from '@/lib/api/terrain';
import { calculateGroundwave } from '@/lib/api/groundwave';
import { createRfDraft, type RfDraft } from '@/lib/map/rfDraft';
import { DEFAULT_RF_INPUTS, type RfInputs } from '@/lib/map/rfPlanning';
import { RF_TERRAIN_CACHE_TTL_MS } from '@/lib/map/rfElevationCache';
import * as automation from '@/lib/map/rfAutomation';
import { createRfTerrainRadials } from '@/lib/map/rfTerrainSampling';
import type { Position } from '@/lib/map/geoJsonTypes';
import type { RfAnalysis } from '@/lib/map/rfAnalysis';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { plainUser, adminUser } from '@/test/fixtures';

vi.mock('@/lib/api/terrain', () => ({ fetchTerrainElevations: vi.fn() }));
vi.mock('@/lib/api/groundwave', () => ({ calculateGroundwave: vi.fn() }));
const fetch = vi.mocked(fetchTerrainElevations);
const groundwave = vi.mocked(calculateGroundwave);
function elevations(count: number): TerrainElevations {
  return {
    elevations_m: Array<number>(count).fill(0),
    zoom: 10,
    resolution_m: 100,
    provider: 'Mapzen Terrain Tiles',
    attribution: 'Test credits',
    attribution_url: 'https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
    limitations: 'Test terrain',
  };
}
interface Props {
  input: RfInputs;
  draft: RfDraft;
  origin: Position;
  receiver: Position | null;
}
function setup(patch: Partial<Props> = {}) {
  const initial: Props = {
    input: DEFAULT_RF_INPUTS,
    draft: createRfDraft(),
    origin: [0, 51],
    receiver: [0.01, 51],
    ...patch,
  };
  const changed = vi.fn<(value: RfAnalysis | null) => void>();
  const hook = renderHook(
    ({ input, draft, origin, receiver }: Props) =>
      useRfAnalysis(input, draft, origin, receiver, changed),
    { initialProps: initial },
  );
  return { ...hook, initial, changed };
}
function latestTerrain(changed: ReturnType<typeof setup>['changed']) {
  const value = changed.mock.calls.at(-1)?.[0];
  if (value?.kind !== 'terrain') throw new Error('Expected a completed terrain analysis.');
  return value;
}
beforeEach(() => {
  fetch
    .mockReset()
    .mockImplementation((positions) => Promise.resolve(elevations(positions.length)));
  groundwave.mockReset().mockResolvedValue({
    status: 'calculated',
    model: 'NTIA LFMF 1.1 (P.368-10)',
    source_url: 'https://github.com/NTIA/LFMF/tree/v1.1',
    limitations: 'Fixture',
    samples: [1, 25].map((distance_km) => ({
      distance_km,
      received_power_dbm: -80,
      basic_transmission_loss_db: 100,
      native_reference_field_dbuv_m: 20,
      method: 'flat_earth',
    })),
  });
  useAuthStore.setState({ user: plainUser, status: 'authenticated' });
});
afterEach(() => {
  vi.restoreAllMocks();
});

it('keeps the initial automatic study explicit and caps an area run at two requests', async () => {
  const { result, rerender, initial, changed } = setup({ receiver: null });
  rerender({ ...initial });
  expect(fetch).not.toHaveBeenCalled();
  expect(changed).not.toHaveBeenCalled();
  await act(() => result.current.analyse());
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(changed).toHaveBeenCalledTimes(2); // Clear, then the final completed study only.
  expect(changed).toHaveBeenLastCalledWith(expect.objectContaining({ kind: 'terrain' }));
  expect(result.current.error).toBeNull();
});

it('discloses a provider-budget reduction of the initial automatic radius even without refinement', async () => {
  vi.spyOn(automation, 'rfStudyRadius').mockReturnValue(25);
  vi.spyOn(automation, 'createAutomaticTerrainPlan').mockReturnValue(
    createRfTerrainRadials([0, 51], 5),
  );
  vi.spyOn(automation, 'rfRefinementRadius').mockReturnValue(null);
  const { result, changed } = setup({ receiver: null });
  await act(() => result.current.analyse());
  expect(fetch).toHaveBeenCalledOnce();
  expect(latestTerrain(changed).terrain.warnings.join(' ')).toContain(
    'reduced from 25.0 to 5.0 km',
  );
  expect(latestTerrain(changed).plan.maxDistanceKm).toBe(5);
});

it('reuses exact path terrain on radio-only edits and requests new data for changed geometry', async () => {
  const { result, rerender, initial, changed } = setup();
  await act(() => result.current.analyse());
  const firstPower = latestTerrain(changed).terrain.path!.receivedDbm!;
  rerender({
    ...initial,
    input: { ...initial.input, transmitDbm: initial.input.transmitDbm + 10 },
  });
  expect(fetch).toHaveBeenCalledOnce();
  await act(() => result.current.analyse());
  expect(fetch).toHaveBeenCalledOnce();
  expect(latestTerrain(changed).terrain.path!.receivedDbm).toBeCloseTo(firstPower + 10);
  rerender({ ...initial, receiver: [0.02, 51] });
  await act(() => result.current.analyse());
  expect(fetch).toHaveBeenCalledTimes(2);
});

it('refetches cached terrain after the five-minute TTL instead of extending its age on reuse', async () => {
  const now = vi.spyOn(Date, 'now').mockReturnValue(1000);
  const { result } = setup();
  await act(() => result.current.analyse());
  now.mockReturnValue(1000 + RF_TERRAIN_CACHE_TTL_MS - 1);
  await act(() => result.current.analyse());
  expect(fetch).toHaveBeenCalledOnce();
  now.mockReturnValue(1000 + RF_TERRAIN_CACHE_TTL_MS);
  await act(() => result.current.analyse());
  expect(fetch).toHaveBeenCalledTimes(2);
});

it.each(['access', 'account', 'role', 'active', 'logout-batch'] as const)(
  'clears cached terrain synchronously after an %s change',
  async (change) => {
    const { result, rerender, initial } = setup();
    await act(() => result.current.analyse());
    act(() => {
      if (change === 'access') invalidateWorkspaceAccess();
      if (change === 'account') useAuthStore.setState({ user: adminUser });
      if (change === 'role') useAuthStore.setState({ user: { ...plainUser, role: 'admin' } });
      if (change === 'active') useAuthStore.setState({ user: { ...plainUser, is_active: false } });
      if (change === 'logout-batch') {
        useAuthStore.setState({ user: null, status: 'anonymous' });
        useAuthStore.setState({ user: plainUser, status: 'authenticated' });
      }
    });
    rerender({ ...initial });
    await act(() => result.current.analyse());
    expect(fetch).toHaveBeenCalledTimes(2);
  },
);

it('does not carry the cache across panel unmount and a new panel instance', async () => {
  const first = setup();
  await act(() => first.result.current.analyse());
  first.unmount();
  const second = setup();
  await act(() => second.result.current.analyse());
  expect(fetch).toHaveBeenCalledTimes(2);
});

it('ignores hidden invalid radius values for an exact receiver terrain path and never refines it', async () => {
  const draft = createRfDraft();
  draft.study = 'link';
  draft.radiusMode = 'manual';
  draft.environment = { ...draft.environment!, radiusKm: '' };
  const refine = vi.spyOn(automation, 'rfRefinementRadius');
  const { result, changed } = setup({ draft });
  await act(() => result.current.analyse());
  expect(result.current.error).toBeNull();
  expect(fetch).toHaveBeenCalledOnce();
  expect(refine).not.toHaveBeenCalled();
  expect(latestTerrain(changed).plan.receiver).toEqual([0.01, 51]);
});

it('resolves HF automatically and uses receiver distance even with an invalid hidden radius', async () => {
  const input = { ...DEFAULT_RF_INPUTS, frequencyMHz: 7 };
  const draft = createRfDraft(input);
  draft.study = 'link';
  draft.radiusMode = 'manual';
  draft.environment = { ...draft.environment!, radiusKm: 'bad' };
  const endpoint = Geodesic.WGS84.Direct(51, 0, 90, 50_000);
  const { result } = setup({ input, draft, receiver: [endpoint.lon2!, endpoint.lat2!] });
  await act(() => result.current.analyse());
  expect(result.current.error).toBeNull();
  expect(groundwave.mock.calls[0]?.[0].max_distance_km).toBeCloseTo(50, 6);
  expect(fetch).not.toHaveBeenCalled();
});

it('excludes a saved receiver from an explicitly selected groundwave area study', async () => {
  const input = { ...DEFAULT_RF_INPUTS, frequencyMHz: 7 };
  const { result, changed } = setup({ input, draft: { ...createRfDraft(input), study: 'area' } });
  await act(() => result.current.analyse());
  expect(result.current.error).toBeNull();
  expect(groundwave.mock.calls[0]?.[0].max_distance_km).toBe(200);
  expect(changed).toHaveBeenLastCalledWith(
    expect.objectContaining({ kind: 'hf-groundwave', receiver: null }),
  );
});

it.each([0.5, 201])(
  'rejects an HF receiver at %s km outside the modelled interval',
  async (distanceKm) => {
    const input = { ...DEFAULT_RF_INPUTS, frequencyMHz: 7 };
    const endpoint = Geodesic.WGS84.Direct(51, 0, 90, distanceKm * 1000);
    const { result } = setup({
      input,
      draft: createRfDraft(input),
      receiver: [endpoint.lon2!, endpoint.lat2!],
    });
    await act(() => result.current.analyse());
    expect(result.current.error).toMatch(/Groundwave receiver distance.*1 to 200/);
    expect(groundwave).not.toHaveBeenCalled();
  },
);

it('exposes progress and explicit cancellation without publishing a late provider result', async () => {
  let finish: (value: TerrainElevations) => void = () => undefined;
  fetch.mockReturnValueOnce(
    new Promise((resolve) => {
      finish = resolve;
    }),
  );
  const { result, changed } = setup();
  let work: Promise<void> | undefined;
  act(() => {
    work = result.current.analyse();
  });
  expect(result.current.progress).toBe('Sampling terrain');
  expect(result.current.busy).toBe(true);
  act(() => result.current.cancel());
  expect(fetch.mock.calls[0]?.[1].aborted).toBe(true);
  expect(result.current.busy).toBe(false);
  expect(result.current.progress).toBeNull();
  await act(async () => {
    finish(elevations(fetch.mock.calls[0]![0].length));
    await work;
  });
  expect(changed.mock.calls.flat()).toEqual([null]);
  await act(() => result.current.analyse());
  expect(fetch).toHaveBeenCalledTimes(2);
});
