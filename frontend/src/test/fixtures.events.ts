/** Live event, store statistics and stream fixtures. */
import type { LiveEvent, StoreStats } from '@/lib/api/eventSchemas';

/** A located, graded live event; override fields per test. */
export function liveEvent(overrides: Partial<LiveEvent> = {}): LiveEvent {
  return {
    id: 'e1',
    source_id: 'usgs_earthquakes',
    category: 'disaster',
    subtype: 'earthquake',
    title: 'M4.2 near Somewhere',
    summary: 'Depth 10 km.',
    url: 'https://example.com/e1',
    published_at: '2026-09-05T00:00:00Z',
    observed_at: '2026-09-05T00:01:00Z',
    language: 'en',
    title_en: null,
    point: { lon: 10, lat: 50 },
    geo_confidence: 'exact',
    country_iso: 'DE',
    tags: ['earthquake'],
    severity: 0.5,
    reliability: 'A',
    credibility: 2,
    grade: 'A2',
    grade_rationale: 'Instrument data',
    story_id: null,
    attributes: { magnitude: 4.2 },
    ...overrides,
  };
}

export const liveEvents: LiveEvent[] = [
  liveEvent(),
  liveEvent({
    id: 'e2',
    source_id: 'cisa_kev',
    category: 'cyber',
    subtype: 'kev',
    title: 'CVE-2026-0001 added to KEV',
    summary: null,
    url: null,
    point: null,
    geo_confidence: 'none',
    published_at: '2026-09-04T12:00:00Z',
    tags: [],
    severity: null,
    reliability: 'B',
    credibility: 1,
    grade: 'B1',
    attributes: {},
  }),
];

export const storeStats: StoreStats = {
  total: 2,
  estimated_bytes: 4096,
  budget_bytes: 1_048_576,
  per_category: [
    {
      category: 'disaster',
      count: 1,
      oldest: '2026-09-05T00:00:00Z',
      newest: '2026-09-05T00:00:00Z',
    },
    { category: 'cyber', count: 1, oldest: '2026-09-04T12:00:00Z', newest: '2026-09-04T12:00:00Z' },
  ],
};
