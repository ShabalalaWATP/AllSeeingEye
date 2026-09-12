import { act, renderHook } from '@testing-library/react';
import { beforeEach, expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { useEventsStore } from '@/stores/events';
import { useDashboardEvents } from './useDashboardEvents';

const now = Date.parse('2026-09-10T12:00:00Z');
const plane = liveEvent({
  id: 'plane',
  category: 'aviation',
  country_iso: 'DE',
  published_at: '2026-09-10T11:00:30Z',
});
const thermal = liveEvent({
  id: 'thermal',
  category: 'disaster',
  subtype: 'thermal_detection',
  source_id: 'firms_viirs_noaa20',
  country_iso: 'FR',
  published_at: '2026-09-10T11:30:00Z',
});
beforeEach(() => {
  useEventsStore.setState({ hidden: [] });
  useEventsStore.getState().applyUpsert([plane, thermal]);
});

it('clears a hidden observation and does not revive its selection when the switch returns', () => {
  const { result } = renderHook(() => useDashboardEvents(now));
  act(() => result.current.fires.toggleEnabled());
  act(() => result.current.select('thermal'));
  expect(result.current.selected?.id).toBe('thermal');
  act(() => result.current.fires.toggleEnabled());
  expect(result.current.selected).toBeNull();
  expect(useEventsStore.getState().selectedId).toBeNull();
  act(() => result.current.fires.toggleEnabled());
  expect(result.current.quality.filtered).toContainEqual(thermal);
  expect(result.current.selected).toBeNull();
});

it('clears category, nation and expired time selections at the final event boundary', () => {
  const { result, rerender } = renderHook(({ at }) => useDashboardEvents(at), {
    initialProps: { at: now },
  });
  act(() => result.current.select('plane'));
  act(() => result.current.toggleCategory('aviation'));
  expect(result.current.selected).toBeNull();
  act(() => {
    result.current.toggleCategory('aviation');
    result.current.select('plane');
  });
  expect(result.current.selected?.id).toBe('plane');
  act(() => result.current.setCountry('FR'));
  expect(result.current.selected).toBeNull();
  act(() => {
    result.current.setCountry(null);
    result.current.setWindow(1);
    result.current.select('plane');
  });
  expect(result.current.selected?.id).toBe('plane');
  rerender({ at: now + 60_000 });
  expect(result.current.selected).toBeNull();
});

it('keeps deliberately inspected unplotted records and clears them only when their quality is excluded', () => {
  const sourceOnly = liveEvent({
    id: 'unplotted',
    category: 'news',
    point: null,
    geo_confidence: 'none',
  });
  useEventsStore.getState().applyUpsert([sourceOnly]);
  const { result } = renderHook(() => useDashboardEvents(now));
  act(() => {
    result.current.quality.setFilter('unplotted');
    result.current.select('unplotted');
  });
  expect(result.current.selected?.id).toBe('unplotted');
  act(() => result.current.quality.setFilter('reported'));
  expect(result.current.selected).toBeNull();
});
