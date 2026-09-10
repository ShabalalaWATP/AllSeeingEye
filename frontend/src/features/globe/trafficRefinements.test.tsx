import { act, fireEvent, render, renderHook, screen, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { useEventsStore } from '@/stores/events';
import {
  aircraftGroundState,
  matchesTrafficRefinement,
  useTrafficRefinements,
} from './trafficRefinements';
import { filterObservations, useObservationFilters } from './ObservationControls';
import { TrafficPanel } from './TrafficPanel';

const aircraft = liveEvent({
  id: 'plane',
  title: 'CALL123',
  category: 'aviation',
  subtype: 'aircraft',
  source_id: 'adsb_a',
  attributes: { on_ground: false, icao_hex: 'abc123' },
});
const grounded = liveEvent({
  ...aircraft,
  id: 'ground',
  title: 'PARKED',
  source_id: 'adsb_b',
  attributes: { on_ground: true },
});
const unknown = liveEvent({
  ...aircraft,
  id: 'unknown',
  title: 'NO FLAG',
  attributes: { altitude_ft: 10000, ground_speed_kt: 100 },
});
const vessel = liveEvent({
  id: 'ship',
  category: 'maritime',
  subtype: 'vessel_position',
  attributes: { mmsi: 12345 },
});
const warning = liveEvent({ id: 'warning', category: 'maritime', subtype: 'hazard' });
const quake = liveEvent({ id: 'quake', category: 'disaster', subtype: 'earthquake' });
const rows = [aircraft, grounded, unknown, vessel, warning, quake];

it('uses explicit reported booleans and never infers flight status from missing flags, altitude or speed', () => {
  expect(aircraftGroundState(aircraft)).toBe('airborne');
  expect(aircraftGroundState(grounded)).toBe('ground');
  expect(aircraftGroundState(unknown)).toBe('unknown');
  for (const on_ground of [null, 'false', 0, '']) {
    expect(aircraftGroundState({ ...aircraft, attributes: { on_ground } })).toBe('unknown');
  }
});

it('combines source, text and status without filtering nontraffic events or unrelated traffic kinds', () => {
  const filter = { query: 'abc123', source: 'adsb_a', ground: 'airborne' as const };
  expect(
    filterObservations(rows, { aircraft: true, vessels: true, firms: true }, 'all', 'all', {
      aircraft: filter,
    }),
  ).toEqual([aircraft, vessel, warning, quake]);
  expect(matchesTrafficRefinement(grounded, 'aircraft', filter)).toBe(false);
  expect(
    matchesTrafficRefinement(vessel, 'vessels', { query: '12345', source: '', ground: 'airborne' }),
  ).toBe(true);
  expect(matchesTrafficRefinement(aircraft, 'aircraft', { ...filter, query: 'missing' })).toBe(
    false,
  );
  expect(
    matchesTrafficRefinement(unknown, 'aircraft', { query: '', source: '', ground: 'unknown' }),
  ).toBe(true);
});

it('preserves defaults, clears excluded selections permanently and retains source choices across filters', () => {
  const { result, rerender } = renderHook(() => useObservationFilters(rows));
  expect(result.current.filtered).toEqual(rows);
  const stable = result.current.filtered;
  rerender();
  expect(result.current.filtered).toBe(stable);
  expect(result.current.trafficRefinements.aircraft.sources).toEqual(['adsb_a', 'adsb_b']);
  act(() => useEventsStore.getState().select(aircraft.id));
  act(() => result.current.trafficRefinements.aircraft.setQuery('  ABC123  '));
  expect(result.current.filtered).toEqual([aircraft, vessel, warning, quake]);
  expect(useEventsStore.getState().selectedId).toBe(aircraft.id);
  act(() => result.current.trafficRefinements.aircraft.setGround('ground'));
  expect(result.current.filtered).toEqual([vessel, warning, quake]);
  expect(useEventsStore.getState().selectedId).toBeNull();
  act(() => result.current.trafficRefinements.aircraft.setGround('all'));
  expect(useEventsStore.getState().selectedId).toBeNull();
  expect(result.current.trafficRefinements.aircraft.sources).toEqual(['adsb_a', 'adsb_b']);
  act(() => result.current.trafficRefinements.aircraft.setQuery('a'.repeat(500)));
  expect(result.current.trafficRefinements.aircraft.query).toHaveLength(100);
});

it('shows identical aircraft membership in the popup and map while keeping a single search control', () => {
  const select = vi.fn();
  function Panel() {
    const state = useObservationFilters(rows);
    return (
      <>
        <TrafficPanel
          kind="aircraft"
          filter={state.flightFilter}
          onChange={state.setFlightFilter}
          events={rows.filter((item) => item.category === 'aviation')}
          onSelect={select}
          count={0}
          refinements={state.trafficRefinements.aircraft}
        />
        <output aria-label="Map traffic">
          {state.filtered
            .filter((item) => item.category === 'aviation')
            .map((item) => item.title)
            .join(',')}
        </output>
      </>
    );
  }
  render(<Panel />);
  expect(screen.getAllByRole('searchbox', { name: 'Search aircraft' })).toHaveLength(1);
  fireEvent.change(screen.getByLabelText('Reported aircraft status'), {
    target: { value: 'unknown' },
  });
  const list = () => screen.getByRole('list', { name: 'aircraft search results' });
  expect(within(list()).getAllByRole('button')).toHaveLength(1);
  expect(within(list()).getByRole('button')).toHaveTextContent('NO FLAG');
  expect(screen.getByLabelText('Map traffic')).toHaveTextContent('NO FLAG');
  fireEvent.change(screen.getByLabelText('Reported aircraft status'), { target: { value: 'all' } });
  fireEvent.change(screen.getByRole('searchbox', { name: 'Search aircraft' }), {
    target: { value: 'abc123' },
  });
  expect(within(list()).getByRole('button')).toHaveTextContent('CALL123');
  expect(screen.getByLabelText('Map traffic')).toHaveTextContent('CALL123');
  fireEvent.click(within(list()).getByRole('button'));
  expect(select).toHaveBeenCalledWith(aircraft);
  fireEvent.change(screen.getByLabelText('Position source'), { target: { value: 'adsb_b' } });
  expect(screen.getByText('No matching aircraft loaded.')).toBeVisible();
  expect(screen.getByLabelText('Map traffic')).toBeEmptyDOMElement();
});

it('has no aircraft-status control for vessels and labels a selected source that is no longer loaded', () => {
  const { result, rerender } = renderHook(
    ({ events }) => useTrafficRefinements(events, 'vessels'),
    { initialProps: { events: rows } },
  );
  act(() => result.current.setSource(vessel.source_id));
  rerender({ events: [] });
  render(<TrafficPanel kind="vessels" filter="all" count={0} refinements={result.current} />);
  expect(screen.queryByLabelText('Reported aircraft status')).not.toBeInTheDocument();
  expect(screen.getByRole('option', { name: /not currently loaded/ })).toBeInTheDocument();
});
