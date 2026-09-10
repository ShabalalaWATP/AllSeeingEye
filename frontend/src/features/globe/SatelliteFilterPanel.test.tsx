import { fireEvent, render, screen } from '@testing-library/react';
import { renderHook, act } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { filterSatellites } from '@/lib/satellites';
import { useSatelliteFilters } from './useSatelliteFilters';
import { SatelliteFilterPanel } from './SatelliteFilterPanel';

const station = liveEvent({
  id: 'station',
  category: 'space',
  subtype: 'satellite',
  source_id: 'celestrak_stations',
  attributes: { norad_id: '25544' },
});
const skynet = liveEvent({
  id: 'skynet',
  category: 'space',
  subtype: 'satellite',
  source_id: 'celestrak_skynet',
  tags: ['skynet'],
  attributes: { norad_id: '39034', military_public_catalogue: true },
});

it('deduplicates public objects and preserves unrelated layers for every filter', () => {
  const general = { ...skynet, id: 'active', source_id: 'celestrak_active' };
  const plane = liveEvent({ id: 'plane', category: 'aviation' });
  expect(filterSatellites([general, skynet, station, plane], 'all')).toEqual([
    plane,
    skynet,
    station,
  ]);
  expect(filterSatellites([skynet, general, station, plane], 'skynet')).toEqual([plane, skynet]);
  expect(filterSatellites([skynet, station, plane], 'crewed')).toEqual([plane, station]);
  expect(filterSatellites([station, skynet, plane], 'military')).toEqual([plane, skynet]);
});

it('handles missing and numeric NORAD IDs, preferring the latest equal-priority estimate', () => {
  const old = { ...station, id: 'old', attributes: { norad_id: 25544 } };
  const latest = { ...station, observed_at: '2026-09-08T00:00:00Z' };
  const unknown = { ...station, id: 'unknown', attributes: {} };
  expect(filterSatellites([old, latest, unknown], 'all')).toEqual([latest, unknown]);
  const military = { ...skynet, source_id: 'celestrak_military' };
  expect(filterSatellites([military], 'military')).toEqual([military]);
});

it('changes the hook filter and shows truthful loaded counts and disclosure', () => {
  vi.spyOn(Date, 'now').mockReturnValue(Date.parse(station.published_at!));
  const { result } = renderHook(() => useSatelliteFilters([station, skynet]));
  expect(result.current.counts).toEqual({ all: 2, crewed: 1, military: 1, skynet: 1 });
  act(() => result.current.setGroup('skynet'));
  expect(result.current.filtered).toEqual([skynet]);
  const change = vi.fn();
  render(<SatelliteFilterPanel {...result.current} group="all" setGroup={change} />);
  fireEvent.click(screen.getByRole('radio', { name: /Skynet/ }));
  expect(change).toHaveBeenCalledWith('skynet');
  expect(screen.getByRole('radio', { name: /All satellites/ })).toHaveAttribute(
    'aria-checked',
    'true',
  );
  expect(screen.getByText(/not live observations/)).toBeInTheDocument();
  expect(screen.getByText(/historical spacecraft/)).toBeInTheDocument();
});

it('hides obsolete or malformed satellite predictions without hiding other layers', () => {
  const now = Date.parse('2026-09-08T12:00:00Z');
  const old = { ...station, attributes: { position_at: '2026-09-08T11:49:59Z' } };
  const current = { ...skynet, attributes: { position_at: '2026-09-08T11:50:00Z' } };
  const future = { ...station, id: 'future', attributes: { position_at: '2026-09-08T12:02:00Z' } };
  const malformed = { ...station, id: 'bad', attributes: { position_at: 'invalid' } };
  const news = liveEvent({ id: 'news' });
  expect(filterSatellites([old, current, future, malformed, news], 'all', now)).toEqual([
    news,
    current,
  ]);
});
