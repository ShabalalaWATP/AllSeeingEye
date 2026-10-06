import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import {
  conflictSourceChoices,
  matchesConflictDisplay,
  type ConflictPrecision,
} from '@/lib/conflictDisplayFilters';
import { isUnreviewedConflictSignal } from '@/lib/conflictReview';
import {
  countConflictReports,
  filterConflictReports,
  isHistoricalConflict,
  type ConflictGroup,
} from '@/lib/conflicts';
import { useEventsStore } from '@/stores/events';
import { liveEvent } from '@/test/fixtures';
import { useConflictFilters } from './useConflictFilters';

interface Options {
  group: ConflictGroup;
  includeHistorical: boolean;
  includeUnreviewed: boolean;
  query: string;
  source: string;
  precision: ConflictPrecision;
}

const defaults: Options = {
  group: 'all',
  includeHistorical: false,
  includeUnreviewed: false,
  query: '',
  source: 'all',
  precision: 'all',
};

// Preserve the former public-helper pipeline as an independent behavioural oracle.
function reference(events: LiveEvent[], options: Options) {
  const searched = events.filter((event) =>
    matchesConflictDisplay(event, options.query, options.source, options.precision),
  );
  const scoped = filterConflictReports(
    searched,
    'all',
    options.includeHistorical,
    options.includeUnreviewed,
  );
  return {
    sourceOptions: conflictSourceChoices(events),
    historicalCount: events.filter(isHistoricalConflict).length,
    unreviewedCount: events.filter(isUnreviewedConflictSignal).length,
    counts: countConflictReports(scoped),
    filtered: filterConflictReports(scoped, options.group, true, options.includeUnreviewed),
  };
}

function configure(filters: ReturnType<typeof useConflictFilters>, options: Options) {
  filters.setGroup(options.group);
  filters.setIncludeHistorical(options.includeHistorical);
  filters.setIncludeUnreviewed(options.includeUnreviewed);
  filters.setQuery(options.query);
  filters.setSource(options.source);
  filters.setPrecision(options.precision);
}

function expectEquivalent(
  actual: ReturnType<typeof useConflictFilters>,
  events: LiveEvent[],
  options: Options,
) {
  const expected = reference(events, options);
  expect(actual.sourceOptions).toEqual(expected.sourceOptions);
  expect(actual.historicalCount).toBe(expected.historicalCount);
  expect(actual.unreviewedCount).toBe(expected.unreviewedCount);
  expect(actual.counts).toEqual(expected.counts);
  expect(actual.filtered).toEqual(expected.filtered);
  expected.filtered.forEach((event, index) => expect(actual.filtered[index]).toBe(event));
}

function records(): LiveEvent[] {
  const conflict = (id: string, overrides: Partial<LiveEvent> = {}) =>
    liveEvent({
      id,
      category: 'conflict',
      subtype: 'fight',
      source_id: 'acled',
      title: 'Kyiv bridge',
      attributes: {},
      tags: [],
      ...overrides,
    });
  return [
    conflict('clash'),
    liveEvent({ id: 'plane', category: 'aviation', source_id: 'air_source' }),
    conflict('monthly', { attributes: { dataset_status: 'provisional_monthly' } }),
    conflict('tagged-monthly', { tags: ['provisional_monthly'], source_id: 'z_source' }),
    conflict('pending', { source_id: 'gdelt_events', subtype: 'protest' }),
    conflict('uncertain', {
      attributes: {
        conflict_screening: 'llm',
        conflict_relevance: 'uncertain',
      },
    }),
    conflict('context', {
      attributes: {
        conflict_screening: 'llm',
        conflict_relevance: 'context',
      },
    }),
    conflict('unrelated', {
      attributes: {
        conflict_screening: 'llm',
        conflict_relevance: 'unrelated',
      },
    }),
    conflict('accepted', {
      attributes: {
        conflict_screening: 'llm',
        conflict_relevance: 'armed_conflict',
      },
    }),
    conflict('riot', {
      source_id: 'gdelt_events',
      subtype: 'protest',
      attributes: {
        event_code: '1451',
        conflict_screening: 'llm',
        conflict_relevance: 'civil_unrest',
      },
    }),
    conflict('city', { subtype: 'protest', geo_confidence: 'city' }),
    conflict('unlocated', { point: null, geo_confidence: 'none' }),
    conflict('machine', { tags: ['machine_coded'], source_id: 'other_source' }),
    liveEvent({ id: 'news', category: 'news', point: null }),
  ];
}

afterEach(() => useEventsStore.getState().reset());

describe('conflict scope equivalence', () => {
  const refinements: Partial<Options>[] = [
    {},
    { group: 'armed_clashes' },
    { group: 'protests' },
    { group: 'riots' },
    { includeHistorical: true },
    { includeUnreviewed: true },
    { includeHistorical: true, includeUnreviewed: true },
    { group: 'other', includeHistorical: true, includeUnreviewed: true },
    { query: '  KYIV bridge  ', source: 'acled', precision: 'exact' },
    { query: 'missing', includeUnreviewed: true },
    { precision: 'approximate', group: 'protests' },
    { source: 'gdelt_events', includeUnreviewed: true, group: 'riots' },
  ];
  it.each(refinements)('preserves each scope and ordered current references for %j', (patch) => {
    const events = records();
    const options = { ...defaults, ...patch };
    const { result } = renderHook(() => useConflictFilters(events));
    act(() => configure(result.current, options));
    expectEquivalent(result.current, events, options);
    expect(result.current.filtered.some((event) => event.id === 'plane')).toBe(true);
    expect(result.current.filtered.some((event) => event.id === 'news')).toBe(true);
    expect(
      result.current.filtered.some((event) => ['context', 'unrelated'].includes(event.id)),
    ).toBe(false);
  });

  it('keeps duplicate records and input order without mutating frozen data', () => {
    const first = records()[0];
    if (first === undefined) throw new Error('Missing test record');
    const second = liveEvent({ ...first, title: 'Corrected duplicate' });
    const events = [first, second, first];
    for (const event of events) {
      Object.freeze(event.attributes);
      Object.freeze(event.tags);
      Object.freeze(event);
    }
    Object.freeze(events);
    const { result } = renderHook(() => useConflictFilters(events));
    expectEquivalent(result.current, events, defaults);
    expect(result.current.counts.all).toBe(3);
    expect(result.current.sourceOptions).toEqual([{ value: 'acled', label: 'acled' }]);
  });

  it('refreshes corrected records and removes expired source choices and raw counts', () => {
    const events = records();
    const options = { ...defaults, includeHistorical: true, includeUnreviewed: true };
    const { result, rerender } = renderHook(({ items }) => useConflictFilters(items), {
      initialProps: { items: events },
    });
    act(() => configure(result.current, options));
    const current = events.find((event) => event.id === 'pending');
    if (current === undefined) throw new Error('Missing pending test record');
    current.source_id = 'current_source';
    current.subtype = 'riot';
    current.tags = [];
    current.attributes = { conflict_screening: 'llm', conflict_relevance: 'civil_unrest' };
    current.point = null;
    current.geo_confidence = 'none';
    const next = events.filter(
      (event) => !['monthly', 'tagged-monthly', 'machine'].includes(event.id),
    );
    rerender({ items: next });
    expectEquivalent(result.current, next, options);
    expect(result.current.filtered.find((event) => event.id === 'pending')).toBe(current);
    expect(result.current.sourceOptions.some((item) => item.value === 'z_source')).toBe(false);
    expect(result.current.historicalCount).toBe(0);
    current.category = 'news';
    current.attributes = { conflict_screening: 'llm', conflict_relevance: 'unrelated' };
    rerender({ items: [...next] });
    expectEquivalent(result.current, next, options);
    expect(result.current.filtered).toContain(current);
    expect(result.current.sourceOptions.some((item) => item.value === 'current_source')).toBe(
      false,
    );
  });

  it('keeps current selection clearing and unrelated selection ownership unchanged', () => {
    const events = records();
    useEventsStore.getState().applyUpsert(events);
    useEventsStore.getState().select('accepted');
    useEventsStore.getState().toggleCategory('conflict');
    const { result, rerender } = renderHook(({ items }) => useConflictFilters(items), {
      initialProps: { items: events },
    });
    const next = events.map((event) =>
      event.id === 'accepted'
        ? liveEvent({
            ...event,
            attributes: {
              conflict_screening: 'llm',
              conflict_relevance: 'context',
            },
          })
        : event,
    );
    rerender({ items: next });
    expect(useEventsStore.getState().selectedId).toBeNull();
    expect(useEventsStore.getState().hidden).toContain('conflict');
    act(() => useEventsStore.getState().select('plane'));
    act(() => result.current.setQuery('no matching conflict'));
    expect(useEventsStore.getState().selectedId).toBe('plane');
    expect(result.current.filtered.some((event) => event.id === 'plane')).toBe(true);
  });

  it('returns empty scopes and zero counts after all input expires', () => {
    const { result, rerender } = renderHook(({ items }) => useConflictFilters(items), {
      initialProps: { items: records() },
    });
    rerender({ items: [] });
    expectEquivalent(result.current, [], defaults);
  });
});
