import { act, fireEvent, render, renderHook, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { DEFAULT_HAZARD_OPTIONS, hazardKind, matchesHazard } from '@/lib/hazards';
import { useEventsStore } from '@/stores/events';
import { HazardFilterPanel } from './HazardFilterPanel';
import { useHazardFilters } from './useHazardFilters';

afterEach(() => {
  useEventsStore.getState().reset();
  vi.useRealTimers();
});
const quake = liveEvent({
  id: 'quake',
  category: 'disaster',
  subtype: 'earthquake',
  attributes: { magnitude: 3 },
});
const thermal = liveEvent({ id: 'thermal', category: 'disaster', subtype: 'thermal_detection' });
const plane = liveEvent({ id: 'plane', category: 'aviation' });
const events = [quake, thermal, plane];

it('exposes truthful type labels, counts and magnitude controls without hiding other layers', () => {
  function Harness() {
    const filters = useHazardFilters(events);
    return (
      <>
        <HazardFilterPanel {...filters} />
        <output aria-label="Shown IDs">
          {filters.filtered.map((event) => event.id).join(',')}
        </output>
      </>
    );
  }
  render(<Harness />);
  fireEvent.change(screen.getByLabelText('Earthquake minimum magnitude'), {
    target: { value: '4' },
  });
  expect(screen.getByLabelText('Shown IDs')).toHaveTextContent('thermal,plane');
  fireEvent.click(screen.getByRole('radio', { name: /Satellite thermal detections/ }));
  expect(screen.getByLabelText('Shown IDs')).toHaveTextContent('thermal,plane');
  expect(screen.getByText(/Thermal pixels do not establish a wildfire/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Reset hazard filters' }));
  expect(screen.getByLabelText('Shown IDs')).toHaveTextContent('quake,thermal,plane');
});

it('clears excluded hazard selections and preserves other selections and layer switches', () => {
  useEventsStore.setState({ hidden: [] });
  useEventsStore.getState().applyUpsert(events);
  useEventsStore.getState().select('quake');
  useEventsStore.getState().toggleCategory('disaster');
  const { result } = renderHook(() => useHazardFilters(events));
  act(() => result.current.updateOptions({ group: 'thermal' }));
  expect(useEventsStore.getState().selectedId).toBeNull();
  expect(useEventsStore.getState().hidden).toContain('disaster');
  act(() => useEventsStore.getState().select('plane'));
  act(() => result.current.updateOptions({ group: 'earthquake' }));
  expect(useEventsStore.getState().selectedId).toBe('plane');
  expect(result.current.counts.all).toBe(2);
});

it('keeps provider scales separate and handles missing values explicitly', () => {
  const unknown = liveEvent({ ...quake, attributes: { severity_value: '9.1' } });
  const options = { ...DEFAULT_HAZARD_OPTIONS, minimumMagnitude: 4 };
  expect(matchesHazard(unknown, options, Date.now())).toBe(true);
  expect(matchesHazard(unknown, { ...options, includeUnknown: false }, Date.now())).toBe(false);
  const green = liveEvent({
    category: 'disaster',
    source_id: 'gdacs',
    subtype: 'flood',
    attributes: { alert_level: 'Green' },
  });
  expect(matchesHazard(green, { ...options, alert: 'orange_red' }, Date.now())).toBe(false);
  expect(
    matchesHazard(thermal, { ...options, alert: 'red', includeUnknown: false }, Date.now()),
  ).toBe(true);
  expect(hazardKind(liveEvent({ category: 'disaster', subtype: 'unexpected' }))).toBe('other');
  expect(hazardKind(liveEvent({ category: 'news', subtype: 'earthquake' }))).toBeNull();
});

it('ages reported times and never substitutes a fresh download time for unknown publication', () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date('2026-09-09T12:00:00Z'));
  const recent = liveEvent({ ...quake, published_at: '2026-09-08T12:00:30Z' });
  const { result } = renderHook(() => useHazardFilters([recent, plane]));
  act(() => result.current.updateOptions({ hours: '24' }));
  expect(result.current.filtered).toHaveLength(2);
  act(() => {
    vi.advanceTimersByTime(60_000);
  });
  expect(result.current.filtered).toEqual([plane]);
  const undated = liveEvent({ ...quake, published_at: null });
  expect(
    matchesHazard(
      undated,
      { ...DEFAULT_HAZARD_OPTIONS, hours: '24', includeUnknown: false },
      Date.now(),
    ),
  ).toBe(false);
  const future = liveEvent({ ...quake, published_at: '2027-01-01T00:00:00Z' });
  expect(matchesHazard(future, { ...DEFAULT_HAZARD_OPTIONS, hours: '24' }, Date.now())).toBe(false);
});
