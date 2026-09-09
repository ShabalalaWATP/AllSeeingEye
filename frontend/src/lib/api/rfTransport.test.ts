import { expect, it, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/server';
import { calculateGroundwave } from './groundwave';
import type { GroundwaveRequest } from './groundwave';
import { fetchTerrainElevations } from './terrain';

const request: GroundwaveRequest = {
  frequency_mhz: 10,
  tx_power_w: 10,
  tx_height_m: 10,
  rx_height_m: 2,
  conductivity_sm: 0.005,
  relative_permittivity: 15,
  surface_refractivity: 301,
  tx_gain_dbi: 0,
  rx_gain_dbi: 0,
  system_loss_db: 0,
  max_distance_km: 25,
  sample_count: 3,
};
const groundResponse = () => ({
  model: 'NTIA LFMF 1.1 (P.368-10)',
  status: 'calculated',
  samples: [1, 13, 25].map((distance_km) => ({
    distance_km,
    basic_transmission_loss_db: 100,
    native_reference_field_dbuv_m: 10,
    received_power_dbm: -60,
    method: 'flat_earth',
  })),
  source_url: 'https://github.com/NTIA/LFMF/tree/v1.1',
  limitations: 'Homogeneous surface model.',
});
const terrainResponse = () => ({
  elevations_m: [-30, 100],
  zoom: 10,
  resolution_m: 100,
  provider: 'Mapzen Terrain Tiles',
  attribution: 'Mapzen data sources',
  attribution_url: 'https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
  limitations: 'Coarse DEM.',
});

it('sends explicit RF inputs and accepts aligned finite model responses', async () => {
  const groundCalled = vi.fn();
  const terrainCalled = vi.fn();
  server.use(
    http.post('/api/radio/groundwave', async ({ request: incoming }) => {
      groundCalled(await incoming.json());
      return HttpResponse.json(groundResponse());
    }),
    http.post('/api/terrain/elevations', async ({ request: incoming }) => {
      terrainCalled(await incoming.json());
      return HttpResponse.json(terrainResponse());
    }),
  );
  const signal = new AbortController().signal;
  expect((await calculateGroundwave(request, signal)).samples).toHaveLength(3);
  expect(groundCalled).toHaveBeenCalledWith(request);
  expect(
    (
      await fetchTerrainElevations(
        [
          [0, 51],
          [1, 52],
        ],
        signal,
      )
    ).elevations_m,
  ).toEqual([-30, 100]);
  expect(terrainCalled).toHaveBeenCalledWith({
    positions: [
      { lon: 0, lat: 51 },
      { lon: 1, lat: 52 },
    ],
  });
});

it.each(['count', 'unordered', 'duplicate', 'start', 'end', 'nonfinite'] as const)(
  'rejects malformed groundwave %s data before map rendering',
  async (problem) => {
    const body = groundResponse();
    if (problem === 'count') body.samples.pop();
    if (problem === 'unordered') body.samples.reverse();
    if (problem === 'duplicate') body.samples[1]!.distance_km = 1;
    if (problem === 'start') body.samples[0]!.distance_km = 2;
    if (problem === 'end') body.samples[2]!.distance_km = 24;
    if (problem === 'nonfinite') body.samples[1]!.received_power_dbm = Infinity;
    server.use(http.post('/api/radio/groundwave', () => HttpResponse.json(body)));
    await expect(calculateGroundwave(request, new AbortController().signal)).rejects.toMatchObject({
      code: 'invalid_response',
    });
  },
);

it.each(['count', 'height', 'zoom', 'resolution', 'nonfinite'] as const)(
  'rejects malformed terrain %s data instead of silently substituting ground',
  async (problem) => {
    const body = terrainResponse();
    if (problem === 'count') body.elevations_m.pop();
    if (problem === 'height') body.elevations_m[0] = 10001;
    if (problem === 'zoom') body.zoom = 9;
    if (problem === 'resolution') body.resolution_m = 0;
    if (problem === 'nonfinite') body.elevations_m[0] = NaN;
    server.use(http.post('/api/terrain/elevations', () => HttpResponse.json(body)));
    await expect(
      fetchTerrainElevations(
        [
          [0, 51],
          [1, 52],
        ],
        new AbortController().signal,
      ),
    ).rejects.toMatchObject({ code: 'invalid_response' });
  },
);
