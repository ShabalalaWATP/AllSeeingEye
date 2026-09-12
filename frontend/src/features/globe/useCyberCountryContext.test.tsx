import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import * as api from '@/lib/api/events';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useCyberFiltersStore } from '@/stores/cyberFilters';
import { applySession } from '@/test/render';
import { countries, liveEvent } from '@/test/fixtures';
import { useCyberCountryContext } from './useCyberCountryContext';
import type { LocationQualityFilter } from './geographicPrecision';

const directory = Object.fromEntries(countries.map((country) => [country.iso2, country]));
const record = liveEvent({
  id: 'claim',
  category: 'cyber',
  subtype: 'ransomware',
  country_iso: 'GB',
  geo_confidence: 'country',
  point: null,
});
const now = Date.now();
afterEach(() => vi.restoreAllMocks());

it('loads nothing until enabled, then uses a bounded snapshot without viewport geometry', async () => {
  applySession('user');
  const fetch = vi.spyOn(api, 'fetchEvents').mockResolvedValue([record]);
  const { result, rerender, unmount } = renderHook(
    ({ enabled }) => useCyberCountryContext(enabled, directory, 'GB', 48, now, 'all'),
    { initialProps: { enabled: false } },
  );
  expect(fetch).not.toHaveBeenCalled();
  rerender({ enabled: true });
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(fetch).toHaveBeenCalledWith(
    { categories: ['cyber'], limit: 500, country: 'GB', since: expect.any(String) },
    expect.any(AbortSignal),
  );
  expect(result.current.groups).toEqual([]);
  unmount();
  expect(fetch.mock.calls[0]?.[1]?.aborted).toBe(true);
});

it('shares kind/search/quality filters with country context and clears excluded selection', async () => {
  applySession('user');
  vi.spyOn(api, 'fetchEvents').mockResolvedValue([
    record,
    { ...record, id: 'outage', subtype: 'outage' },
  ]);
  const { result, rerender } = renderHook(
    ({ quality }) => useCyberCountryContext(true, directory, null, null, now, quality),
    { initialProps: { quality: 'all' as LocationQualityFilter } },
  );
  await waitFor(() => expect(result.current.events).toHaveLength(2));
  act(() => useCyberFiltersStore.getState().setCountryContext(true));
  expect(result.current.groups).toHaveLength(1);
  act(() => result.current.select('GB'));
  expect(result.current.selected?.events).toHaveLength(2);
  act(() => useCyberFiltersStore.getState().setKind('outage_signal'));
  expect(result.current.events.map((event) => event.id)).toEqual(['outage']);
  act(() => useCyberFiltersStore.getState().setQuery('unmatched'));
  expect(result.current.selected).toBeNull();
  act(() => useCyberFiltersStore.getState().setQuery(''));
  expect(result.current.selected).toBeNull();
  rerender({ quality: 'reported' });
  expect(result.current.groups).toEqual([]);
  rerender({ quality: 'unplotted' });
  expect(result.current.groups).toHaveLength(1);
});

it('bounds oversized results, handles errors and refreshes without retaining superseded records', async () => {
  applySession('user');
  const fetch = vi
    .spyOn(api, 'fetchEvents')
    .mockResolvedValue(
      Array.from({ length: 501 }, (_, index) => ({ ...record, id: String(index) })),
    );
  const { result } = renderHook(() =>
    useCyberCountryContext(true, directory, null, null, now, 'all'),
  );
  await waitFor(() => expect(result.current.limited).toBe(true));
  expect(result.current.events).toHaveLength(500);
  fetch.mockRejectedValueOnce(new Error('offline'));
  act(() => result.current.refresh());
  expect(result.current.events).toEqual([]);
  await waitFor(() => expect(result.current.error).toBeTruthy());
  expect(result.current.events).toEqual([]);
});

it('discards snapshots across batched logout/login and rejects late responses after access changes', async () => {
  applySession('user');
  const fetch = vi.spyOn(api, 'fetchEvents').mockResolvedValue([record]);
  const { result } = renderHook(() =>
    useCyberCountryContext(true, directory, null, null, now, 'all'),
  );
  await waitFor(() => expect(result.current.events).toHaveLength(1));
  let resolve!: (events: LiveEvent[]) => void;
  fetch.mockImplementation(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  act(() => {
    applySession('anonymous');
    applySession('user');
  });
  expect(result.current.events).toEqual([]);
  expect(fetch).toHaveBeenCalledTimes(2);
  const staleResolve = resolve;
  act(() => invalidateWorkspaceAccess());
  await act(async () => {
    staleResolve([record]);
    await Promise.resolve();
  });
  expect(result.current.events).toEqual([]);
  expect(fetch.mock.calls[1]?.[1]?.aborted).toBe(true);
});
