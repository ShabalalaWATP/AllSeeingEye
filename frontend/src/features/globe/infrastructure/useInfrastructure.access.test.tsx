import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import * as api from '@/lib/api/infrastructure';
import type { Infrastructure } from '@/lib/api/infrastructure';
import { useAuthStore } from '@/stores/auth';
import { plainUser } from '@/test/fixtures';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useInfrastructure } from './useInfrastructure';

const plant: api.NuclearFacility = {
  id: 'plant',
  name: 'Historical plant',
  country: 'Country',
  country_code: 'GBR',
  longitude: 0,
  latitude: 51,
  capacity_mw: null,
  capacity_year: null,
  operator: null,
  source_name: 'WRI',
  source_url: 'http://example.org/',
  geolocation_source: 'WRI',
  note: 'Historical approximate location',
};
const data: Infrastructure = {
  cables: [],
  ground_stations: [],
  nuclear_facilities: [plant],
  snapshot_date: '2026-09-09',
  cable_attribution: 'OSM',
  cable_licence_url: 'https://example.org/',
  nuclear_attribution: 'WRI',
  nuclear_licence_url: 'https://example.org/',
  nuclear_dataset_version: 'test',
  nuclear_snapshot_date: '2026-09-09',
};
afterEach(() => vi.restoreAllMocks());

it('aborts on logout and ignores a late result even when the transport resolves anyway', async () => {
  useAuthStore.setState({ status: 'authenticated', user: plainUser });
  let finish!: (value: Infrastructure) => void;
  const fetch = vi.spyOn(api, 'fetchInfrastructure').mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const { result } = renderHook(() => useInfrastructure());
  act(() => result.current.toggleNuclear());
  const signal = fetch.mock.calls[0]?.[0];
  act(() => useAuthStore.getState().clearSession());
  expect(signal?.aborted).toBe(true);
  await act(async () => {
    finish(data);
    await Promise.resolve();
  });
  expect(result.current.data).toBeNull();
  expect(result.current.loading).toBe(false);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it('hides previous data and choices immediately on access changes until a fresh response', async () => {
  useAuthStore.setState({ status: 'authenticated', user: plainUser });
  const fetch = vi
    .spyOn(api, 'fetchInfrastructure')
    .mockResolvedValueOnce(data)
    .mockImplementation(() => new Promise(() => undefined));
  const { result } = renderHook(() => useInfrastructure());
  act(() => result.current.toggleNuclear());
  await waitFor(() => expect(result.current.data).toEqual(data));
  act(() => result.current.select({ kind: 'nuclear', item: plant }));
  expect(result.current.selected?.item).toEqual(plant);
  act(() => invalidateWorkspaceAccess());
  expect(result.current.data).toBeNull();
  expect(result.current.selected).toBeNull();
  expect(result.current.loading).toBe(true);
  expect(fetch).toHaveBeenCalledTimes(2);
});
