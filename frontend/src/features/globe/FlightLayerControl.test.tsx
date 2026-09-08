import { render, screen, fireEvent, renderHook, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { useEventsStore } from '@/stores/events';
import { useObservationFilters, filterObservations } from './ObservationControls';
import { MapLayerRail } from './MapLayerRail';

const military = liveEvent({ id: 'mil', category: 'aviation', subtype: 'military_aircraft' });
const flagged = liveEvent({ id: 'flag', category: 'aviation', tags: ['military'] });
const unclassified = liveEvent({
  id: 'other',
  category: 'aviation',
  title: 'RAF military plane',
  tags: [],
  subtype: 'aircraft',
});
const boat = liveEvent({
  id: 'boat',
  category: 'maritime',
  subtype: 'vessel_position',
  tags: ['military'],
});
const events = [military, flagged, unclassified, boat];

it('filters explicit military labels without guessing from titles or removing other layers', () => {
  expect(
    filterObservations(events, { aircraft: true, vessels: true, firms: true }, 'military'),
  ).toEqual([military, flagged, boat]);
  expect(
    filterObservations(events, { aircraft: false, vessels: true, firms: true }, 'military'),
  ).toEqual([boat]);
  useEventsStore.setState({ selectedId: unclassified.id });
  const { result } = renderHook(() => useObservationFilters(events));
  act(() => result.current.setFlightFilter('military'));
  expect(useEventsStore.getState().selectedId).toBeNull();
  expect(result.current.filtered).toEqual([military, flagged, boat]);
  act(() => result.current.toggle('aircraft'));
  expect(result.current.filtered).toEqual([boat]);
  act(() => result.current.toggle('aircraft'));
  expect(result.current.flightFilter).toBe('military');
});

it('opens a labelled flight submenu, applies the filter and keeps its switch functional', async () => {
  useEventsStore.setState({ hidden: [] });
  function Rail() {
    const state = useObservationFilters(events);
    return (
      <>
        <MapLayerRail
          events={events}
          counts={{}}
          visibility={state.visibility}
          onToggle={state.toggle}
          flightFilter={state.flightFilter}
          onFlightFilter={state.setFlightFilter}
        />
        <output aria-label="Visible aircraft">
          {state.filtered.map((event) => event.id).join(',')}
        </output>
      </>
    );
  }
  const user = userEvent.setup();
  render(<Rail />);
  const opener = screen.getByRole('button', { name: 'Flight filters' });
  await user.click(opener);
  expect(screen.getByRole('button', { name: 'Close flight filters' })).toHaveFocus();
  expect(screen.getByText('2 provider-labelled military aircraft loaded')).toBeInTheDocument();
  await user.click(screen.getByRole('radio', { name: 'Military only' }));
  expect(screen.getByLabelText('Visible aircraft')).toHaveTextContent('mil,flag,boat');
  expect(screen.getByRole('switch', { name: 'Flights 2' })).toBeChecked();
  await user.keyboard('{Escape}');
  expect(opener).toHaveFocus();
  expect(screen.queryByRole('region', { name: 'Flight filters' })).not.toBeInTheDocument();
  await user.click(screen.getByRole('switch', { name: 'Flights 2' }));
  expect(screen.getByLabelText('Visible aircraft')).toHaveTextContent('boat');
  await user.click(opener);
  await user.click(screen.getByRole('radio', { name: 'All aircraft' }));
  expect(screen.getByRole('switch', { name: 'Flights 3' })).not.toBeChecked();
  await user.click(screen.getByRole('button', { name: 'Close flight filters' }));
  expect(opener).toHaveFocus();
  await user.click(opener);
  fireEvent.pointerDown(document.body);
  expect(opener).toHaveAttribute('aria-expanded', 'false');
  await user.click(opener);
  await user.click(opener);
  expect(opener).toHaveAttribute('aria-expanded', 'false');
});

it('applies the boat military filter to the map and clears a filtered selection', async () => {
  const civilian = liveEvent({
    id: 'civil-ship',
    category: 'maritime',
    subtype: 'vessel_position',
  });
  const vessels = [boat, civilian];
  useEventsStore.setState({ hidden: [], selectedId: civilian.id });
  function Rail() {
    const state = useObservationFilters(vessels);
    return (
      <>
        <MapLayerRail
          events={vessels}
          counts={{}}
          visibility={state.visibility}
          onToggle={state.toggle}
          vesselFilter={state.vesselFilter}
          onVesselFilter={state.setVesselFilter}
          onTrafficSelect={() => undefined}
        />
        <output aria-label="Visible vessels">
          {state.filtered.map((event) => event.id).join(',')}
        </output>
      </>
    );
  }
  const user = userEvent.setup();
  render(<Rail />);
  await user.click(screen.getByRole('button', { name: 'Boat list' }));
  await user.click(screen.getByRole('radio', { name: 'Military only' }));
  expect(screen.getByLabelText('Visible vessels')).toHaveTextContent(/^boat$/);
  expect(screen.getByRole('switch', { name: 'Boats 1' })).toBeChecked();
  expect(useEventsStore.getState().selectedId).toBeNull();
  await user.click(screen.getByRole('radio', { name: 'All vessels' }));
  expect(screen.getByLabelText('Visible vessels')).toHaveTextContent('boat,civil-ship');
});
