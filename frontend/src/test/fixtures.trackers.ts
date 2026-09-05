/** Tracker boards and details built from the live event fixture. */
import type { ConflictCard, ConflictDetail, HazardCard, HazardDetail } from '@/lib/api/trackers';

import { liveEvent } from './fixtures.events';

const quake = liveEvent({ id: 'q1', title: 'M6.1 quake', severity: 0.9, country_iso: 'JP' });

export const hazardCard: HazardCard = {
  hazard: 'earthquake',
  title: 'Earthquakes',
  activity: { last_24h: 1, last_7d: 3, previous_7d: 1, trend: 3.0 },
  red_alerts: 1,
  max_severity: 0.9,
  countries: ['JP', 'ID'],
  latest: quake,
  top: quake,
};

export const hazardDetail: HazardDetail = {
  card: hazardCard,
  timeline: Array.from({ length: 14 }, (_, index) => ({
    day: `2026-08-${String(23 + index).padStart(2, '0')}`.replace('2026-08-32', '2026-09-01'),
    count: index === 13 ? 3 : 0,
    max_severity: index === 13 ? 0.9 : null,
  })),
  events: [quake, liveEvent({ id: 'q2', title: 'M4.5 quake', severity: 0.3, country_iso: 'JP' })],
};

const shelling = liveEvent({
  id: 'k1',
  source_id: 'gdelt_events',
  category: 'conflict',
  subtype: 'battle',
  title: 'Shelling in Kharkiv',
  point: { lon: 36.2, lat: 49.9 },
  country_iso: 'UA',
  grade: 'C3',
  severity: 0.7,
});

export const conflictCard: ConflictCard = {
  conflict: {
    id: 'ukraine',
    name: "Russia's war in Ukraine",
    status: 'war',
    countries: ['UA'],
    bbox: [22, 44, 41, 52.5],
    belligerents: ['Russia', 'Ukraine'],
    keywords: ['Ukraine', 'Kharkiv'],
    summary: 'Full-scale war since February 2022.',
  },
  activity: { last_24h: 2, last_7d: 12, previous_7d: 20, trend: 0.6 },
  reporting_7d: 5,
  fatalities_7d: 4,
  max_severity: 0.9,
  latest: shelling,
  top: shelling,
};

export const conflictDetail: ConflictDetail = {
  card: conflictCard,
  timeline: hazardDetail.timeline,
  events: [shelling, liveEvent({ id: 'n1', category: 'news', title: 'Talks in Kyiv', url: null })],
};
