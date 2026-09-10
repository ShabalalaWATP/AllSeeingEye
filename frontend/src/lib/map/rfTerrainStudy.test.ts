import { beforeEach, expect, it, vi } from 'vitest';
import { runRfTerrainStudy } from './rfTerrainStudy';
import { RfElevationCache } from './rfElevationCache';
import { createRfTerrainPath, createRfTerrainRadials } from './rfTerrainSampling';
import { DEFAULT_RF_INPUTS } from './rfPlanning';
import { RF_PHYSICAL_REFERENCE } from './rfEngineering';
import { fetchTerrainElevations, type TerrainElevations } from '@/lib/api/terrain';
import * as automation from './rfAutomation';
import { Geodesic } from 'geographiclib-geodesic';

vi.mock('@/lib/api/terrain', () => ({ fetchTerrainElevations: vi.fn() }));
const fetch = vi.mocked(fetchTerrainElevations);
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
function request(refine = true) {
  return {
    input: { ...DEFAULT_RF_INPUTS, transmitHeightM: 100, receiveHeightM: 100 },
    engineering: RF_PHYSICAL_REFERENCE,
    plan: createRfTerrainRadials([0, 51], 5),
    refine,
    cache: new RfElevationCache(),
    signal: new AbortController().signal,
    onProgress: vi.fn<(message: string) => void>(),
  };
}
beforeEach(() => {
  vi.restoreAllMocks();
  fetch
    .mockReset()
    .mockImplementation((positions) => Promise.resolve(elevations(positions.length)));
  vi.spyOn(automation, 'rfRefinementRadius').mockReturnValue(10);
});

it('performs at most one extra pass and returns only the completed refinement', async () => {
  const inputs = request();
  const result = await runRfTerrainStudy(inputs);
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(automation.rfRefinementRadius).toHaveBeenCalledOnce();
  expect(result.plan.maxDistanceKm).toBe(10);
  expect(result.terrain.warnings.join(' ')).toContain('refined once to 10.0 km');
  expect(inputs.onProgress.mock.calls.flat()).toEqual([
    'Sampling terrain',
    'Refining estimated coverage',
  ]);
});

it('does not refine manual areas, receiver paths or studies without a recommendation', async () => {
  await runRfTerrainStudy(request(false));
  expect(fetch).toHaveBeenCalledOnce();
  await runRfTerrainStudy({ ...request(), plan: createRfTerrainPath([0, 51], [0.01, 51]) });
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(automation.rfRefinementRadius).not.toHaveBeenCalled();
  vi.mocked(automation.rfRefinementRadius).mockReturnValue(null);
  await runRfTerrainStudy(request());
  expect(fetch).toHaveBeenCalledTimes(3);
});

it('fails the initial request without manufacturing results or caching incomplete terrain', async () => {
  const inputs = request();
  fetch.mockRejectedValueOnce(new Error('Provider failure'));
  await expect(runRfTerrainStudy(inputs)).rejects.toThrow('Provider failure');
  expect(fetch).toHaveBeenCalledOnce();
  expect(inputs.cache.get(inputs.plan.positions)).toBeNull();
  fetch.mockResolvedValueOnce(elevations(1));
  await expect(runRfTerrainStudy(inputs)).rejects.toThrow(/complete finite/);
  expect(inputs.cache.get(inputs.plan.positions)).toBeNull();
});

it('retains the initial screen with a safe warning when the optional second request fails', async () => {
  const inputs = request();
  fetch
    .mockResolvedValueOnce(elevations(409))
    .mockRejectedValueOnce(new Error('Private provider payload'));
  const result = await runRfTerrainStudy(inputs);
  expect(result.plan).toEqual(inputs.plan);
  expect(result.terrain.warnings.join(' ')).toContain(
    'The first completed terrain screen is shown',
  );
  expect(result.terrain.warnings.join(' ')).not.toContain('Private provider payload');
  expect(fetch).toHaveBeenCalledTimes(2);
});

it.each(['same', 'smaller', 'failure'] as const)(
  'does not replace a useful initial screen when expansion planning is %s',
  async (mode) => {
    const inputs = request();
    vi.spyOn(automation, 'createAutomaticTerrainPlan').mockImplementation(() => {
      if (mode === 'failure') throw new Error('Unsupported tiles');
      return mode === 'same' ? inputs.plan : createRfTerrainRadials([0, 51], 2);
    });
    const result = await runRfTerrainStudy(inputs);
    expect(result.plan.maxDistanceKm).toBe(5);
    expect(fetch).toHaveBeenCalledOnce();
    expect(result.terrain.warnings.join(' ')).toContain('Automatic refinement was unavailable');
  },
);

it('recomputes radio analysis using cached terrain without repeating either provider request', async () => {
  const inputs = request();
  const first = await runRfTerrainStudy(inputs);
  const second = await runRfTerrainStudy({
    ...inputs,
    input: { ...inputs.input, transmitDbm: -100 },
  });
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(second.terrain.radials.some((radial) => radial.status === 'risk')).toBe(true);
  expect(first.terrain.radials.some((radial) => radial.clearDistanceKm > 0)).toBe(true);
  expect(inputs.onProgress.mock.calls.flat().slice(-2)).toEqual([
    'Reusing sampled terrain',
    'Reusing sampled terrain',
  ]);
});

it('cancels refinement instead of publishing the initial result or caching its late response', async () => {
  const inputs = request();
  const controller = new AbortController();
  let finish: (result: TerrainElevations) => void = () => undefined;
  fetch.mockResolvedValueOnce(elevations(409)).mockReturnValueOnce(
    new Promise((resolve) => {
      finish = resolve;
    }),
  );
  const work = runRfTerrainStudy({ ...inputs, signal: controller.signal });
  const rejected = expect(work).rejects.toMatchObject({ name: 'AbortError' });
  await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  controller.abort();
  finish(elevations(409));
  await rejected;
  expect(inputs.cache.get(createRfTerrainRadials([0, 51], 10).positions)).toBeNull();
});

it('honours cancellation before inspecting a cached result', async () => {
  const inputs = request(false);
  await runRfTerrainStudy(inputs);
  const controller = new AbortController();
  controller.abort();
  await expect(runRfTerrainStudy({ ...inputs, signal: controller.signal })).rejects.toMatchObject({
    name: 'AbortError',
  });
  expect(fetch).toHaveBeenCalledOnce();
});

it('retains a known narrow ridge when automatic expansion uses a wider grid that misses it', async () => {
  vi.mocked(automation.rfRefinementRadius).mockRestore();
  const inputs = request();
  fetch.mockImplementation((positions) => {
    const result = elevations(positions.length);
    result.elevations_m = positions.map(([lon, lat]) => {
      const distance = Geodesic.WGS84.Inverse(51, 0, lat, lon).s12!;
      return Math.abs(lon) < 0.000001 && lat > 51 && distance >= 150 && distance <= 160 ? 500 : 0;
    });
    return Promise.resolve(result);
  });
  const result = await runRfTerrainStudy(inputs);
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(result.plan.maxDistanceKm).toBe(10);
  expect(result.elevations.elevations_m).toContain(500);
  expect(result.terrain.radials[0]?.status).toBe('blocked');
  expect(result.terrain.radials[0]?.clearDistanceKm).toBeLessThan(1);
  expect(result.plan.positions.length).toBeGreaterThan(409);
  expect(result.terrain.sampleCount).toBe(result.plan.positions.length);
});
