import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import {
  DEFAULT_NEWS_OPTIONS,
  isNewsCategory,
  matchesNews,
  newsStories,
  useNewsFilters,
} from './newsFilters';

describe('News filtering', () => {
  const article = liveEvent({
    category: 'news',
    title: 'Un titre original',
    title_en: 'Port talks resume',
    summary: 'Negotiators discuss transport policy.',
    source_id: 'bbc_world',
    country_iso: 'GB',
  });

  it.each([' ORIGINAL ', 'PORT TALKS', 'transport policy', 'BBC_WORLD', 'gb'])(
    'finds reporting by original/translated headline, summary, source and declared country: %s',
    (query) => expect(matchesNews(article, { ...DEFAULT_NEWS_OPTIONS, query })).toBe(true),
  );

  it('combines subjects, exact publisher and text without inferring geography', () => {
    const options = { ...DEFAULT_NEWS_OPTIONS, source: 'bbc_world', query: 'policy' };
    expect(matchesNews(article, options)).toBe(true);
    expect(matchesNews({ ...article, source_id: 'bbc_world_copy' }, options)).toBe(false);
    expect(matchesNews({ ...article, category: 'political' }, options)).toBe(false);
    expect(matchesNews(article, { ...options, categories: [] })).toBe(false);
    const unlocated = {
      ...article,
      point: null,
      country_iso: null,
      geo_confidence: 'none' as const,
    };
    expect(matchesNews(unlocated, { ...DEFAULT_NEWS_OPTIONS, query: 'GB' })).toBe(false);
    expect(matchesNews(unlocated, DEFAULT_NEWS_OPTIONS)).toBe(true);
    expect(unlocated.point).toBeNull();
    expect(unlocated.country_iso).toBeNull();
  });

  it('owns only reporting subjects and preserves other map categories', () => {
    const political = liveEvent({ id: 'policy', category: 'political' });
    const flight = liveEvent({ id: 'flight', category: 'aviation' });
    const events = [article, political, flight];
    const { result, rerender } = renderHook(({ enabled }) => useNewsFilters(events, enabled), {
      initialProps: { enabled: false },
    });
    expect(result.current.filtered).toEqual([flight]);
    expect(result.current.count).toBe(1);
    act(() =>
      result.current.setOptions({ categories: ['news', 'political'], source: '', query: '' }),
    );
    expect(result.current.count).toBe(2);
    expect(result.current.filtered).toEqual([flight]);
    rerender({ enabled: true });
    expect(result.current.filtered).toEqual(events);
    act(() => result.current.setOptions({ categories: [], source: '', query: '' }));
    expect(result.current.filtered).toEqual([flight]);
    expect(result.current.count).toBe(0);
    expect(
      ['news', 'political', 'humanitarian', 'economic', 'social'].every((category) =>
        isNewsCategory(category as typeof article.category),
      ),
    ).toBe(true);
    expect(isNewsCategory('conflict')).toBe(false);
    expect(isNewsCategory('cyber')).toBe(false);
  });
});

describe('Related reporting', () => {
  it('groups declared story identities and identical links with the newest publication leading', () => {
    const older = liveEvent({ id: 'older', story_id: 'story', url: 'https://one.example/old' });
    const newer = liveEvent({
      id: 'newer',
      story_id: 'story',
      url: 'https://two.example/new',
      published_at: '2026-09-06T00:00:00Z',
    });
    const linked = liveEvent({ id: 'linked', url: 'https://three.example/shared' });
    const duplicate = liveEvent({ ...linked, id: 'duplicate' });
    const input = [older, linked, newer, duplicate];
    const stories = newsStories(input);
    expect(stories).toEqual([
      { lead: newer, records: [newer, older] },
      { lead: linked, records: [linked, duplicate] },
    ]);
    expect(input).toEqual([older, linked, newer, duplicate]);
  });

  it('keeps similar titles and unlinked records separate and never substitutes retrieval time', () => {
    const dated = liveEvent({ id: 'dated', url: 'https://one.example/news' });
    const sameTitle = liveEvent({ id: 'same-title', url: 'https://two.example/news' });
    const unknown = liveEvent({
      id: 'unknown',
      url: null,
      published_at: null,
      observed_at: '2027-01-01T00:00:00Z',
    });
    const another = liveEvent({ ...unknown, id: 'another' });
    expect(
      newsStories([unknown, dated, another, sameTitle]).map(({ lead, records }) => [
        lead.id,
        records.length,
      ]),
    ).toEqual([
      ['dated', 1],
      ['same-title', 1],
      ['unknown', 1],
      ['another', 1],
    ]);
  });
});
