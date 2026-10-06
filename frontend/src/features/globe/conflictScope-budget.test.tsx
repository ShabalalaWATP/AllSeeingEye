import { renderHook } from '@testing-library/react';
import { afterEach, expect, it } from 'vitest';
import { useEventsStore } from '@/stores/events';
import { liveEvent } from '@/test/fixtures';
import { useConflictFilters } from './useConflictFilters';

afterEach(() => useEventsStore.getState().reset());

it('does not repeat the review decision for final grouping of an already eligible scope', () => {
  let screeningReads = 0;
  const events = Array.from({ length: 32 }, (_, index) => {
    const attributes = { conflict_relevance: 'armed_conflict' };
    Object.defineProperty(attributes, 'conflict_screening', {
      enumerable: true,
      get() {
        // Constant output measures classification work without affecting eligibility.
        screeningReads++;
        return 'llm';
      },
    });
    return liveEvent({
      id: `reviewed-${index}`,
      category: 'conflict',
      subtype: 'fight',
      source_id: 'acled',
      attributes,
      tags: [],
    });
  });
  const { result } = renderHook(() => useConflictFilters(events));
  // Raw unreviewed count, eligibility and kind each need the current screening field.
  // Final group selection must not perform a fourth screening decision per record.
  expect(screeningReads).toBeLessThanOrEqual(events.length * 3);
  expect(result.current.filtered).toEqual(events);
  expect(result.current.counts.armed_clashes).toBe(events.length);
  expect(result.current.unreviewedCount).toBe(0);
  events.forEach((event, index) => expect(result.current.filtered[index]).toBe(event));
});
