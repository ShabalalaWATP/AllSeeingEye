import { act, fireEvent, render, renderHook, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import {
  countFires,
  countHazards,
  DEFAULT_HAZARD_OPTIONS,
  fireKind,
  matchesHazard,
} from '@/lib/hazards';
import { useEventsStore } from '@/stores/events';
import { HazardFilterPanel } from './HazardFilterPanel';
import { FiresFilterPanel } from './FiresFilterPanel';
import { useHazardFilters } from './useHazardFilters';
import { useFiresFilters } from './useFiresFilters';
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

it('separates wildfire reports and thermal detections from natural hazard counts and source refinements', () => {
  const options = {
    ...DEFAULT_HAZARD_OPTIONS,
    groups: [],
    hours: '24' as const,
    alert: 'red' as const,
    includeUnknown: false,
  };
  const olderFire = {
    ...alert,
    published_at: '2020-01-01T00:00:00Z',
    attributes: { alert_level: 'green' },
  };
  expect(matchesHazard(olderFire, options, Date.now())).toBe(true);
  expect(countHazards(events)).toMatchObject({ all: 1, volcano: 1 });
  expect(countFires(events)).toEqual({ all: 3, wildfire: 2, thermal: 1 });
  expect(fireKind({ ...wildfire, subtype: 'wildfires_unconfirmed' })).toBeNull();
});

it('starts Fires off, remembers source choices and allows either source or both independently from natural hazards', () => {
  function Harness() {
    const hazards = useHazardFilters(events);
    const fires = useFiresFilters(hazards.filtered);
    return (
      <>
        <HazardFilterPanel {...hazards} />
        <FiresFilterPanel {...fires} />
        <button type="button" onClick={fires.toggleEnabled}>
          Toggle Fires master
        </button>
        <output aria-label="Visible IDs">
          {fires.filtered.map((event) => event.id).join(',')}
        </output>
      </>
    );
  }
  render(<Harness />);
  const shown = () => screen.getByLabelText('Visible IDs').textContent;
  expect(shown()).toBe('volcano,plane');
  expect(screen.getByText(/Fires is off/)).toBeInTheDocument();
  expect(screen.getByRole('checkbox', { name: /^FIRMS thermal detections/ })).toBeChecked();
  expect(screen.getByRole('checkbox', { name: /^Reported wildfires/ })).toBeChecked();
  fireEvent.click(screen.getByRole('button', { name: 'Clear hazard types' }));
  expect(shown()).toBe('plane');
  fireEvent.click(screen.getByRole('button', { name: 'Toggle Fires master' }));
  expect(shown()).toBe('wildfire,alert,thermal,plane');
  fireEvent.click(screen.getByRole('checkbox', { name: /^FIRMS thermal detections/ }));
  expect(shown()).toBe('wildfire,alert,plane');
  fireEvent.click(screen.getByRole('checkbox', { name: /^Reported wildfires/ }));
  expect(shown()).toBe('plane');
  expect(screen.getByText('No fire evidence types selected.')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('checkbox', { name: /^FIRMS thermal detections/ }));
  expect(shown()).toBe('thermal,plane');
  fireEvent.click(screen.getByRole('button', { name: 'Select all hazard types' }));
  expect(shown()).toBe('thermal,volcano,plane');
  fireEvent.click(screen.getByRole('button', { name: 'Toggle Fires master' }));
  expect(shown()).toBe('volcano,plane');
  fireEvent.click(screen.getByRole('button', { name: 'Toggle Fires master' }));
  expect(shown()).toBe('thermal,volcano,plane');
  expect(useEventsStore.getState().hidden).toContain('disaster');
});

it('clears excluded fire selections without clearing unrelated selections or restoring disabled source choices', () => {
  useEventsStore.getState().applyUpsert(events);
  const { result } = renderHook(() => useFiresFilters(events));
  act(() => result.current.toggleEnabled());
  act(() => useEventsStore.getState().select('thermal'));
  act(() => result.current.updateOptions({ thermal: false }));
  expect(useEventsStore.getState().selectedId).toBeNull();
  act(() => useEventsStore.getState().select('plane'));
  act(() => result.current.toggleEnabled());
  expect(useEventsStore.getState().selectedId).toBe('plane');
  act(() => result.current.toggleEnabled());
  expect(result.current.options.thermal).toBe(false);
  expect(result.current.filtered).toEqual([wildfire, alert, volcano, plane]);
  act(() => useEventsStore.getState().select('wildfire'));
  act(() => result.current.toggleEnabled());
  expect(useEventsStore.getState().selectedId).toBeNull();
});

it.each([false, true])(
  'uses independently filtered source rows in map/globe rendering (globe=%s)',
  (globe) => {
    const { result } = renderHook(() => {
      const hazards = useHazardFilters(events);
      const fires = useFiresFilters(hazards.filtered);
      return { hazards, fires };
    });
    act(() => result.current.hazards.updateOptions({ groups: [] }));
    act(() => result.current.fires.toggleEnabled());
    const icons = () =>
      buildEventLayers(result.current.fires.filtered, [], vi.fn(), null, {
        zoom: 10,
        globe,
        onCluster: vi.fn(),
      }).find((layer) => layer.id === 'event-icons')?.props.data;
    expect(icons()).toEqual([wildfire, alert, thermal, plane]);
    act(() => result.current.fires.updateOptions({ wildfire: false }));
    expect(icons()).toEqual([thermal, plane]);
    act(() => result.current.fires.updateOptions({ thermal: false, wildfire: true }));
    expect(icons()).toEqual([wildfire, alert, plane]);
  },
);
