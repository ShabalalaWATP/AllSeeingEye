import { act, fireEvent, render, renderHook, screen, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { useSatelliteFilters } from './useSatelliteFilters';
import { SatelliteFilterPanel } from './SatelliteFilterPanel';
import { matchesSatelliteSearch, satelliteIdentifiers } from './satelliteSearch';

const now = '2026-09-10T12:00:00Z';
const satellite = liveEvent({
  id: 'iss',
  category: 'space',
  subtype: 'satellite',
  title: 'ISS (ZARYA)',
  source_id: 'celestrak_stations',
  published_at: now,
  attributes: { norad_id: 25544, object_id: '1998-067A', position_at: now },
});

it('searches catalogue names, numeric NORAD IDs and designators without guessing missing fields', () => {
  for (const query of ['iss', '25544', '1998-067a', 'zarya 25544']) {
    expect(matchesSatelliteSearch(satellite, query.split(/\s+/))).toBe(true);
  }
  expect(matchesSatelliteSearch(satellite, ['hubble'])).toBe(false);
  expect(matchesSatelliteSearch({ ...satellite, attributes: { norad_id: true } }, ['true'])).toBe(
    false,
  );
  expect(satelliteIdentifiers(satellite)).toBe('NORAD 25544 · 1998-067A');
  expect(satelliteIdentifiers({ ...satellite, attributes: {} })).toBe('');
});

it('shares current deduplicated search results with the map while preserving other event categories', () => {
  vi.spyOn(Date, 'now').mockReturnValue(Date.parse(now));
  const plane = liveEvent({ id: 'plane', category: 'aviation', title: 'Unrelated aircraft' });
  const duplicate = { ...satellite, id: 'active:iss', source_id: 'celestrak_active' };
  const stale = {
    ...satellite,
    id: 'stale',
    attributes: { norad_id: 999, position_at: '2026-09-10T10:00:00Z' },
  };
  const rows = [plane, duplicate, satellite, stale];
  const { result } = renderHook(() => useSatelliteFilters(rows));
  expect(result.current.group).toBe('all');
  expect(result.current.results).toEqual([satellite]);
  act(() => result.current.setQuery('  1998-067A  '));
  expect(result.current.filtered).toEqual([plane, satellite]);
  expect(result.current.results).toEqual([satellite]);
  act(() => result.current.setQuery('missing'));
  expect(result.current.filtered).toEqual([plane]);
  expect(result.current.results).toEqual([]);
  expect(result.current.counts.all).toBe(1);
  act(() => result.current.setQuery('x'.repeat(1000)));
  expect(result.current.query).toHaveLength(200);
  act(() => result.current.setQuery(''));
  expect(result.current.results).toEqual([satellite]);
  act(() => result.current.setGroup('skynet'));
  expect(result.current.filtered).toEqual([plane]);
});

it('keeps layer and result references stable on clock ticks until a prediction expires', () => {
  vi.useFakeTimers();
  try {
    vi.setSystemTime(now);
    const rows = [satellite];
    const { result, unmount } = renderHook(() => useSatelliteFilters(rows));
    const filtered = result.current.filtered;
    const results = result.current.results;
    act(() => {
      vi.advanceTimersByTime(30_000);
    });
    expect(result.current.filtered).toBe(filtered);
    expect(result.current.results).toBe(results);
    act(() => {
      vi.advanceTimersByTime(10 * 60_000);
    });
    expect(result.current.results).toEqual([]);
    unmount();
  } finally {
    vi.useRealTimers();
  }
});

it('bounds satellite rows to25, locates selections and resets pagination when search changes', () => {
  const results = Array.from({ length: 5000 }, (_, index) => ({
    ...satellite,
    id: String(index),
    title: `Satellite ${index}`,
  }));
  const select = vi.fn();
  const props = {
    group: 'all' as const,
    setGroup: vi.fn(),
    counts: { all: 5000, crewed: 5000, military: 0, skynet: 0 },
    query: '',
    setQuery: vi.fn(),
    results,
    searching: false,
    onSelect: select,
    selectedId: '25',
  };
  const { rerender } = render(<SatelliteFilterPanel {...props} />);
  const list = screen.getByRole('list', { name: 'Matching satellites' });
  expect(within(list).getAllByRole('button')).toHaveLength(25);
  expect(screen.queryByRole('button', { name: /Satellite 25 / })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Next satellites' }));
  const selected = within(list).getAllByRole('button')[0]!;
  expect(selected).toHaveTextContent('Satellite 25');
  expect(selected).toHaveAttribute('aria-pressed', 'true');
  fireEvent.click(selected);
  expect(select).toHaveBeenCalledWith(results[25]);
  fireEvent.change(screen.getByRole('searchbox', { name: 'Find a satellite' }), {
    target: { value: 'iss' },
  });
  expect(props.setQuery).toHaveBeenCalledWith('iss');
  rerender(<SatelliteFilterPanel {...props} query="iss" />);
  expect(
    within(screen.getByRole('list', { name: 'Matching satellites' })).getAllByRole('button')[0],
  ).toHaveTextContent('Satellite 0');
  rerender(<SatelliteFilterPanel {...props} results={[]} />);
  expect(screen.getByText(/No current satellite positions match/)).toBeVisible();
});
