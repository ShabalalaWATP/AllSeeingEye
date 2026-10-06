import { renderHook } from '@testing-library/react';
import { expect, it } from 'vitest';

import { liveEventSchema } from '@/lib/api/eventSchemas';
import { useEventsStore } from '@/stores/events';
import { liveEvent } from '@/test/fixtures';
import { useObservationFilters } from './ObservationControls';
import { useDashboardSelection } from './useDashboardSelection';
import { useFiresFilters } from './useFiresFilters';
import { useHazardFilters } from './useHazardFilters';

function watchedEvents(prefix: string) {
  let reads = 0;
  const events = Array.from({ length: 64 }, (_, index) => {
    const event = liveEventSchema.parse(liveEvent({ id: `${prefix}-${index}`, category: 'news' }));
    const id = event.id;
    // Count real record visits without replacing find, the hook or its filters.
    Object.defineProperty(event, 'id', {
      enumerable: true,
      get: () => {
        reads++;
        return id;
      },
    });
    return Object.freeze(event);
  });
  Object.freeze(events);
  return { events, reads: () => reads };
}

it.each([
  ['dashboard', useDashboardSelection],
  ['observations', useObservationFilters],
  ['hazards', useHazardFilters],
  ['fires', useFiresFilters],
] as const)(
  '%s does not search event IDs without a selection, including a new batch',
  (_, useSubject) => {
    const first = watchedEvents('first');
    const next = watchedEvents('next');
    const before = useEventsStore.getState();
    expect(before.selectedId).toBeNull();
    const { rerender } = renderHook(({ events }) => useSubject(events), {
      initialProps: { events: first.events },
    });

    expect(first.reads()).toBe(0);
    rerender({ events: next.events });
    expect(next.reads()).toBe(0);
    expect(useEventsStore.getState().selectedId).toBeNull();
    expect(useEventsStore.getState().byId).toBe(before.byId);
    expect(useEventsStore.getState().list).toBe(before.list);
  },
);
