import { act, renderHook } from '@testing-library/react';
import { beforeEach, expect, it } from 'vitest';
import { useAuthStore } from '@/stores/auth';
import { useEventsStore } from '@/stores/events';
import { liveEvent, plainUser, tokenFor } from '@/test/fixtures';
import { useContextSelection } from './context/useContextSelection';
import { DEFAULT_NEWS_OPTIONS } from './newsFilters';
import type { NewsOptions } from './newsFilters';
import { useNewsSelectionGuard } from './useNewsSelectionGuard';
import type { LocationQualityFilter } from './geographicPrecision';

const now = Date.parse('2026-09-13T12:00:00Z');
const headline = liveEvent({
  category: 'news',
  source_id: 'bbc_world',
  title: 'Port talks resume',
  summary: null,
  published_at: '2026-09-11T12:00:00Z',
  country_iso: 'GB',
  point: null,
  geo_confidence: 'none',
});
const defaults = {
  options: DEFAULT_NEWS_OPTIONS,
  windowHours: 168 as number | null,
  now,
  enabled: true,
  quality: 'all' as LocationQualityFilter,
};

function harness(props = defaults) {
  return renderHook(
    (scope) => {
      const context = useContextSelection('GB', false, 'globe');
      useNewsSelectionGuard(
        context,
        { news: scope, quality: { filter: scope.quality }, windowHours: scope.windowHours },
        scope.now,
      );
      return context;
    },
    { initialProps: props },
  );
}

beforeEach(() => useAuthStore.getState().setSession(tokenFor(plainUser)));

it.each([
  ['query', { query: 'unrelated' }],
  ['publisher', { source: 'guardian_world' }],
  ['subjects', { categories: [] }],
] satisfies [string, Partial<NewsOptions>][])(
  'clears excluded %s selections and never revives them when filters are broadened',
  (_name, change) => {
    const { result, rerender } = harness();
    act(() => result.current.choose(headline));
    expect(result.current.event).toBe(headline);
    rerender({ ...defaults, options: { ...DEFAULT_NEWS_OPTIONS, ...change } });
    expect(result.current.event).toBeNull();
    rerender(defaults);
    expect(result.current.event).toBeNull();
  },
);

it('keeps explicit unlocated inspection usable while the News map layer is off', () => {
  useEventsStore.setState({ hidden: ['news'] });
  const { result, rerender } = harness();
  act(() => result.current.choose(headline));
  rerender({
    ...defaults,
    enabled: false,
    options: { ...DEFAULT_NEWS_OPTIONS, query: ' PORT ', source: 'bbc_world' },
  });
  expect(result.current.event).toBe(headline);
  expect(result.current.layers).toEqual([]);
  expect(useEventsStore.getState().hidden).toContain('news');
});

it('clears country-story context when News is switched off or its location quality is excluded', () => {
  const { result, rerender } = harness();
  const event = { ...headline, geo_confidence: 'country' as const };
  act(() => result.current.choose(event));
  rerender({ ...defaults, enabled: false });
  expect(result.current.event).toBeNull();
  rerender(defaults);
  act(() => result.current.choose(event));
  rerender({ ...defaults, quality: 'reported' });
  expect(result.current.event).toBeNull();
});

it.each(['news', 'political', 'humanitarian', 'economic', 'social'] as const)(
  'guards the %s reporting subject without depending on the general-news category',
  (category) => {
    const props = { ...defaults, options: { ...DEFAULT_NEWS_OPTIONS, categories: [category] } };
    const { result, rerender } = harness(props);
    const event = { ...headline, category };
    act(() => result.current.choose(event));
    expect(result.current.event).toBe(event);
    rerender({ ...defaults, options: { ...DEFAULT_NEWS_OPTIONS, categories: [] } });
    expect(result.current.event).toBeNull();
  },
);

it('clears the inspector and context marker when the selected publication falls outside a shorter period', () => {
  const { result, rerender } = harness();
  act(() =>
    result.current.choose({ ...headline, point: { lon: 0, lat: 51 }, geo_confidence: 'city' }),
  );
  expect(result.current.layers).toHaveLength(1);
  rerender({ ...defaults, windowHours: 24 });
  expect(result.current.event).toBeNull();
  expect(result.current.layers).toEqual([]);
  rerender(defaults);
  expect(result.current.event).toBeNull();
});

it('ages a selection out after the inclusive publication boundary passes', () => {
  const props = { ...defaults, windowHours: 48 };
  const { result, rerender } = harness(props);
  act(() => result.current.choose(headline));
  expect(result.current.event).toBe(headline);
  rerender({ ...props, now: now + 1 });
  expect(result.current.event).toBeNull();
});

it.each([null, 'invalid-date'])(
  'keeps unknown dates only in the unbounded view, never substituting retrieval time (%s)',
  (published_at) => {
    const { result, rerender } = harness({ ...defaults, windowHours: null });
    const unknown = { ...headline, published_at, observed_at: new Date(now).toISOString() };
    act(() => result.current.choose(unknown));
    expect(result.current.event).toBe(unknown);
    rerender({ ...defaults, windowHours: 24 });
    expect(result.current.event).toBeNull();
  },
);

it.each(['cyber', 'disaster', 'space'] as const)(
  'leaves unrelated %s context selections intact',
  (category) => {
    const { result, rerender } = harness();
    const event = { ...headline, category };
    act(() => result.current.choose(event));
    rerender({
      ...defaults,
      windowHours: 1,
      options: { categories: [], query: 'exclude', source: 'another' },
    });
    expect(result.current.event).toBe(event);
  },
);
