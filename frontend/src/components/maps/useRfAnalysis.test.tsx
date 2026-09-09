import { act, renderHook } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { useRfAnalysis } from './useRfAnalysis';
import { fetchTerrainElevations } from '@/lib/api/terrain';
import type { TerrainElevations } from '@/lib/api/terrain';
import { calculateGroundwave } from '@/lib/api/groundwave';
import type { GroundwaveResult } from '@/lib/api/groundwave';
import { ApiError } from '@/lib/api/errors';
import { createRfDraft, RF_ENVIRONMENT_DEFAULTS } from '@/lib/map/rfDraft';
import type { RfDraft } from '@/lib/map/rfDraft';
import { DEFAULT_RF_INPUTS } from '@/lib/map/rfPlanning';
import type { RfInputs } from '@/lib/map/rfPlanning';
import type { RfAnalysis } from '@/lib/map/rfAnalysis';
import type { Position } from '@/lib/map/geoJsonTypes';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser } from '@/test/fixtures';

vi.mock('@/lib/api/terrain', () => ({ fetchTerrainElevations: vi.fn() }));
vi.mock('@/lib/api/groundwave', () => ({ calculateGroundwave: vi.fn() }));
const terrain = vi.mocked(fetchTerrainElevations);
const groundwave = vi.mocked(calculateGroundwave);
function elevations(length: number): TerrainElevations {
  return {
    elevations_m: Array<number>(length).fill(0),
    zoom: 10,
    resolution_m: 100,
    provider: 'Mapzen Terrain Tiles',
    attribution: 'Mapzen',
    attribution_url: 'https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
    limitations: 'Coarse test DEM.',
  };
}
const groundResult: GroundwaveResult = {
  model: 'NTIA LFMF 1.1 (P.368-10)',
  status: 'calculated',
  source_url: 'https://github.com/NTIA/LFMF/tree/v1.1',
  limitations: 'Test fixture.',
  samples: Array.from({ length: 48 }, (_, index) => ({
    distance_km: 1 + (index * 24) / 47,
    basic_transmission_loss_db: 100,
    native_reference_field_dbuv_m: 10,
    received_power_dbm: -70,
    method: 'flat_earth' as const,
  })),
};
beforeEach(() => {
  vi.clearAllMocks();
  terrain.mockImplementation((positions) => Promise.resolve(elevations(positions.length)));
  groundwave.mockResolvedValue(groundResult);
  useAuthStore.setState({ user: plainUser, status: 'authenticated' });
});
interface Props {
  input: RfInputs;
  draft: RfDraft;
  origin: Position | null;
  receiver: Position | null;
}
function setup(patch: Partial<Props> = {}) {
  const initial: Props = {
    input: DEFAULT_RF_INPUTS,
    draft: createRfDraft(),
    origin: [0, 51],
    receiver: null,
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
function deferred<T>() {
  let resolve: (value: T) => void = () => undefined;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

it('does no automatic network work and only publishes an explicitly requested terrain analysis', async () => {
  const { result, rerender, initial, changed } = setup();
  rerender({ ...initial, input: { ...initial.input, distanceKm: NaN } });
  expect(terrain).not.toHaveBeenCalled();
  expect(groundwave).not.toHaveBeenCalled();
  expect(changed).not.toHaveBeenCalled();
  await act(() => result.current.analyse());
  expect(terrain).toHaveBeenCalledOnce();
  expect(terrain.mock.calls[0]?.[0]).toHaveLength(409);
  expect(changed).toHaveBeenLastCalledWith(expect.objectContaining({ kind: 'terrain' }));
  expect(result.current.busy).toBe(false);
  expect(result.current.error).toBeNull();
});

it('keeps skywave independent of unrelated power, mast and free-space distance inputs', async () => {
  const input = {
    ...DEFAULT_RF_INPUTS,
    frequencyMHz: 10,
    distanceKm: NaN,
    transmitDbm: NaN,
    transmitHeightM: NaN,
    receiveHeightM: NaN,
    sensitivityDbm: NaN,
  };
  const { result, changed } = setup({
    input,
    draft: { ...createRfDraft(input), propagation: 'hf-skywave' },
  });
  await act(() => result.current.analyse());
  expect(result.current.error).toBeNull();
  expect(changed).toHaveBeenLastCalledWith(expect.objectContaining({ kind: 'hf-skywave' }));
  expect(terrain).not.toHaveBeenCalled();
  expect(groundwave).not.toHaveBeenCalled();
});

it.each(['radiusKm', 'conductivitySm', 'permittivity', 'refractivity'] as const)(
  'rejects a blank groundwave %s locally rather than coercing it to zero',
  async (field) => {
    const { result } = setup({
      input: { ...DEFAULT_RF_INPUTS, frequencyMHz: 10 },
      draft: {
        ...createRfDraft(),
        propagation: 'hf-groundwave',
        environment: { ...RF_ENVIRONMENT_DEFAULTS, [field]: '  ' },
      },
    });
    await act(() => result.current.analyse());
    expect(result.current.error).toMatch(/Enter a valid/);
    expect(groundwave).not.toHaveBeenCalled();
  },
);

it.each(['minElevationDeg', 'maxElevationDeg', 'criticalFrequencyMHz', 'virtualHeightKm'] as const)(
  'rejects an empty skywave %s rather than interpreting a valid zero angle',
  async (field) => {
    const { result } = setup({
      input: { ...DEFAULT_RF_INPUTS, frequencyMHz: 10 },
      draft: {
        ...createRfDraft(),
        propagation: 'hf-skywave',
        environment: { ...RF_ENVIRONMENT_DEFAULTS, [field]: '' },
      },
    });
    await act(() => result.current.analyse());
    expect(result.current.error).toMatch(/Enter a valid/);
  },
);

it('validates native groundwave limits and converts transmit dBm to watts without requiring manual distance', async () => {
  const input = { ...DEFAULT_RF_INPUTS, frequencyMHz: 10, transmitDbm: 40, distanceKm: NaN };
  const { result, initial, rerender, changed } = setup({
    input,
    draft: { ...createRfDraft(input), propagation: 'hf-groundwave' },
  });
  await act(() => result.current.analyse());
  expect(groundwave.mock.calls[0]?.[0]).toMatchObject({
    tx_power_w: 10,
    frequency_mhz: 10,
    max_distance_km: 25,
    sample_count: 48,
  });
  expect(changed).toHaveBeenLastCalledWith(expect.objectContaining({ kind: 'hf-groundwave' }));
  rerender({ ...initial, input: { ...input, transmitHeightM: 51 } });
  await act(() => result.current.analyse());
  expect(result.current.error).toMatch(/0 to 50/);
  expect(groundwave).toHaveBeenCalledOnce();
});

it('does not revive an aborted busy state when draft A changes to B and back to A', async () => {
  const pending = deferred<TerrainElevations>();
  terrain.mockReturnValueOnce(pending.promise);
  const { result, initial, rerender, changed } = setup();
  let work: Promise<void> | undefined;
  act(() => {
    work = result.current.analyse();
  });
  expect(result.current.busy).toBe(true);
  const signal = terrain.mock.calls[0]?.[1];
  rerender({
    ...initial,
    draft: { ...initial.draft, environment: { ...RF_ENVIRONMENT_DEFAULTS, radiusKm: '20' } },
  });
  expect(signal?.aborted).toBe(true);
  rerender(initial);
  expect(result.current.busy).toBe(false);
  await act(async () => {
    pending.resolve(elevations(409));
    await work;
  });
  expect(changed.mock.calls.map(([value]) => value)).toEqual([null]);
  expect(result.current.error).toBeNull();
});

it('keeps the newest request busy when an older cancelled request finishes', async () => {
  const old = deferred<TerrainElevations>();
  const newest = deferred<TerrainElevations>();
  terrain.mockReturnValueOnce(old.promise).mockReturnValueOnce(newest.promise);
  const { result, changed } = setup();
  let first: Promise<void> | undefined, second: Promise<void> | undefined;
  act(() => {
    first = result.current.analyse();
  });
  act(() => {
    second = result.current.analyse();
  });
  expect(terrain.mock.calls[0]?.[1].aborted).toBe(true);
  await act(async () => {
    old.resolve(elevations(409));
    await first;
  });
  expect(result.current.busy).toBe(true);
  expect(changed.mock.calls.map(([value]) => value)).toEqual([null, null]);
  await act(async () => {
    newest.resolve(elevations(409));
    await second;
  });
  expect(result.current.busy).toBe(false);
  expect(changed).toHaveBeenLastCalledWith(expect.objectContaining({ kind: 'terrain' }));
});

it.each(['origin', 'receiver', 'input', 'access', 'account', 'role', 'unmount'] as const)(
  'cancels stale terrain work after %s changes even if the provider resolves after abort',
  async (change) => {
    const pending = deferred<TerrainElevations>();
    terrain.mockReturnValueOnce(pending.promise);
    const { result, initial, rerender, unmount, changed } = setup();
    let work: Promise<void> | undefined;
    act(() => {
      work = result.current.analyse();
    });
    const signal = terrain.mock.calls[0]?.[1];
    if (change === 'origin') rerender({ ...initial, origin: [1, 51] });
    if (change === 'receiver') rerender({ ...initial, receiver: [1, 51] });
    if (change === 'input')
      rerender({ ...initial, input: { ...initial.input, frequencyMHz: 950 } });
    if (change === 'access') act(() => invalidateWorkspaceAccess());
    if (change === 'account') act(() => useAuthStore.setState({ user: adminUser }));
    if (change === 'role')
      act(() => useAuthStore.setState({ user: { ...plainUser, role: 'admin' } }));
    if (change === 'unmount') unmount();
    expect(signal?.aborted).toBe(true);
    await act(async () => {
      pending.resolve(elevations(409));
      await work;
    });
    expect(changed.mock.calls.map(([value]) => value)).toEqual([null]);
    if (change !== 'unmount') expect(result.current.busy).toBe(false);
  },
);

it('shows actionable validation errors, preserves safe API failures and clears them on input changes', async () => {
  const { result, initial, rerender } = setup({ origin: null });
  await act(() => result.current.analyse());
  expect(result.current.error).toMatch(/Place a transmitter/);
  expect(terrain).not.toHaveBeenCalled();
  rerender({ ...initial, origin: [0, 51] });
  expect(result.current.error).toBeNull();
  terrain.mockRejectedValueOnce(
    new ApiError(503, 'terrain_unavailable', 'Terrain is unavailable. Try again later.'),
  );
  await act(() => result.current.analyse());
  expect(result.current.error).toBe('Terrain is unavailable. Try again later.');
  expect(result.current.busy).toBe(false);
});
