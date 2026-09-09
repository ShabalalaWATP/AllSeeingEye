import { act, fireEvent, render, renderHook, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { countHazards, DEFAULT_HAZARD_OPTIONS, matchesHazard } from '@/lib/hazards';
import { useEventsStore } from '@/stores/events';
import { HazardFilterPanel } from './HazardFilterPanel';
import { useHazardFilters } from './useHazardFilters';
import { filterObservations } from './ObservationControls';
import { buildEventLayers } from './layers/registry';

const wildfire = liveEvent({
  id: 'wildfire',
  source_id: 'nasa_eonet',
  category: 'disaster',
  subtype: 'wildfires',
});
const alert = liveEvent({
  id: 'alert',
  source_id: 'gdacs',
  category: 'disaster',
  subtype: 'wildfire',
});
const thermal = liveEvent({
  id: 'thermal',
  source_id: 'firms_viirs_noaa20',
  category: 'disaster',
  subtype: 'thermal_detection',
});
const volcano = liveEvent({ id: 'volcano', category: 'disaster', subtype: 'volcano' });
const plane = liveEvent({ id: 'plane', category: 'aviation' });
const events = [wildfire, alert, thermal, volcano, plane];

afterEach(() => useEventsStore.getState().reset());

it('combines reported wildfires and heat observations once without admitting other disasters', () => {
  const options = { ...DEFAULT_HAZARD_OPTIONS, group: 'fires' as const };
  expect(events.filter((event) => matchesHazard(event, options, Date.now()))).toEqual([
    wildfire,
    alert,
    thermal,
    plane,
  ]);
  expect(countHazards(events)).toMatchObject({ all: 4, fires: 3, wildfire: 2, thermal: 1 });
  expect(
    matchesHazard(
      liveEvent({ category: 'disaster', subtype: 'wildfires_unconfirmed' }),
      options,
      Date.now(),
    ),
  ).toBe(false);
});

it('offers a combined Fires choice and narrower source-type choices while preserving other layers', () => {
  function Harness() {
    const filters = useHazardFilters(events);
    return (
      <>
        <HazardFilterPanel {...filters} />
        <output aria-label="Visible IDs">
          {filters.filtered.map((event) => event.id).join(',')}
        </output>
      </>
    );
  }
  render(<Harness />);
  fireEvent.click(screen.getByRole('radio', { name: /^Fires:/ }));
  expect(screen.getByLabelText('Visible IDs')).toHaveTextContent('wildfire,alert,thermal,plane');
  fireEvent.click(screen.getByRole('radio', { name: /Wildfire alerts/ }));
  expect(screen.getByLabelText('Visible IDs')).toHaveTextContent('wildfire,alert,plane');
  fireEvent.click(screen.getByRole('radio', { name: /Satellite thermal detections/ }));
  expect(screen.getByLabelText('Visible IDs')).toHaveTextContent('thermal,plane');
  fireEvent.click(screen.getByRole('button', { name: 'Reset hazard filters' }));
  expect(screen.getByLabelText('Visible IDs')).toHaveTextContent(
    'wildfire,alert,thermal,volcano,plane',
  );
});

it('retains selection within Fires, clears excluded hazards and honours existing switches', () => {
  useEventsStore.getState().applyUpsert(events);
  useEventsStore.getState().select('thermal');
  const { result } = renderHook(() => useHazardFilters(events));
  act(() => result.current.updateOptions({ group: 'fires' }));
  expect(useEventsStore.getState().selectedId).toBe('thermal');
  act(() => result.current.updateOptions({ group: 'wildfire' }));
  expect(useEventsStore.getState().selectedId).toBeNull();
  const withoutFirms = filterObservations(events, { aircraft: true, vessels: true, firms: false });
  const { result: hidden } = renderHook(() => useHazardFilters(withoutFirms));
  act(() => hidden.current.updateOptions({ group: 'fires' }));
  expect(hidden.current.filtered).toEqual([wildfire, alert, plane]);
  expect(hidden.current.counts).toMatchObject({ fires: 2, thermal: 0 });
  const mapLayers = buildEventLayers(hidden.current.filtered, ['disaster'], vi.fn(), null);
  expect(
    mapLayers.every(
      (layer) =>
        !(layer.props.data as typeof events).some((event) => event.category === 'disaster'),
    ),
  ).toBe(true);
  expect(useEventsStore.getState().hidden).toContain('disaster');
});
