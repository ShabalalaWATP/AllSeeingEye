import { act, renderHook } from '@testing-library/react';
import { expect, it } from 'vitest';

import { liveEventSchema } from '@/lib/api/eventSchemas';
import { useEventsStore } from '@/stores/events';
import { liveEvent } from '@/test/fixtures';
import { useObservationFilters } from './ObservationControls';
import { useFiresFilters } from './useFiresFilters';
import { useHazardFilters } from './useHazardFilters';

it.each(['selected', ''])('clears newly excluded traffic for selected ID %j', (id) => {
  const original = liveEventSchema.parse(
    liveEvent({ id, category: 'aviation', subtype: 'aircraft_position', tags: ['military'] }),
  );
  const corrected = Object.freeze({ ...original, tags: [] });
  Object.freeze(original);
  useEventsStore.setState({ selectedId: id });
  const { result, rerender } = renderHook(({ events }) => useObservationFilters(events), {
    initialProps: { events: [original] },
  });
  act(() => result.current.setFlightFilter('military'));
  expect(useEventsStore.getState().selectedId).toBe(id);
  expect(result.current.filtered[0]).toBe(original);

  rerender({ events: [corrected] });
  expect(result.current.filtered).toHaveLength(0);
  expect(useEventsStore.getState().selectedId).toBeNull();
});

it.each(['selected', ''])('clears newly excluded hazards for selected ID %j', (id) => {
  const original = liveEventSchema.parse(
    liveEvent({ id, category: 'disaster', subtype: 'earthquake', attributes: { magnitude: 5 } }),
  );
  const corrected = Object.freeze({ ...original, attributes: { magnitude: 2 } });
  Object.freeze(original);
  useEventsStore.setState({ selectedId: id });
  const { result, rerender } = renderHook(({ events }) => useHazardFilters(events), {
    initialProps: { events: [original] },
  });
  act(() => result.current.updateOptions({ minimumMagnitude: 4 }));
  expect(useEventsStore.getState().selectedId).toBe(id);
  expect(result.current.filtered[0]).toBe(original);

  rerender({ events: [corrected] });
  expect(result.current.filtered).toHaveLength(0);
  expect(useEventsStore.getState().selectedId).toBeNull();
});

it.each(['selected', ''])('clears newly excluded fire evidence for selected ID %j', (id) => {
  const original = liveEventSchema.parse(
    liveEvent({ id, category: 'disaster', subtype: 'wildfire' }),
  );
  const corrected = Object.freeze({ ...original, subtype: 'thermal_detection' });
  Object.freeze(original);
  const { result, rerender } = renderHook(({ events }) => useFiresFilters(events), {
    initialProps: { events: [original] },
  });
  act(() => {
    result.current.toggleEnabled();
    result.current.updateOptions({ thermal: false });
    useEventsStore.getState().select(id);
  });
  expect(useEventsStore.getState().selectedId).toBe(id);
  expect(result.current.filtered[0]).toBe(original);

  rerender({ events: [corrected] });
  expect(result.current.filtered).toHaveLength(0);
  expect(useEventsStore.getState().selectedId).toBeNull();
});
