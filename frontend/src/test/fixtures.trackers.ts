/** Tracker boards and details built from the live event fixture. */
import type { AviationBoard, JamMap } from '@/lib/api/aviation';
import type { CyberBoard, MaritimeBoard, SpaceBoard } from '@/lib/api/modules';
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
  fatalities_upper_7d: null,
  fatalities_unknown_incidents: 0,
  fatalities_disputed_incidents: 0,
  other_activity_7d: 0,
  unknown_date_reports: 0,
  collapsed_reports_7d: 0,
  max_severity: 0.9,
  latest: shelling,
  top: shelling,
};

export const conflictDetail: ConflictDetail = {
  evidence_groups: [],
  card: conflictCard,
  timeline: hazardDetail.timeline,
  events: [shelling, liveEvent({ id: 'n1', category: 'news', title: 'Talks in Kyiv', url: null })],
};

export const aviationBoard: AviationBoard = {
  military_total: 96,
  interesting: 4,
  ladd: 12,
  pia: 1,
  by_country: [
    { iso: 'US', count: 40, baseline: 32.5, ratio: 1.23 },
    { iso: 'UA', count: 9, baseline: 3, ratio: 3 },
    { iso: 'PL', count: 2, baseline: null, ratio: null },
  ],
  emergencies: [
    liveEvent({
      id: 'sos',
      category: 'aviation',
      subtype: 'emergency',
      title: 'RCH123 (C17): squawk 7700, general emergency',
      severity: 0.8,
      point: { lon: 30, lat: 50 },
      country_iso: 'PL',
      url: 'https://globe.adsb.lol/?icao=ae1234',
    }),
  ],
  areas: [
    {
      id: 'black_sea',
      name: 'Black Sea and southern Ukraine',
      count: 120,
      military: 6,
      baseline: 110,
    },
    { id: 'baltic', name: 'Baltic Sea and Kaliningrad', count: 80, military: 2, baseline: null },
  ],
  jam_amber: 3,
  jam_red: 1,
  jam_updated_at: '2026-09-05T08:30:00Z',
};

export const jamMap: JamMap = {
  cells: [
    { lon: 36.5, lat: 49.5, size: 1, good: 4, bad: 2, percent_bad: 16.7, level: 'red' },
    { lon: 20.5, lat: 55.5, size: 1, good: 30, bad: 2, percent_bad: 3.1, level: 'amber' },
    { lon: 0.5, lat: 51.5, size: 1, good: 200, bad: 1, percent_bad: 0, level: 'green' },
  ],
  updated_at: '2026-09-05T08:30:00Z',
};

export const maritimeBoard: MaritimeBoard = {
  warnings_total: 2,
  located: 1,
  by_area: [
    { key: '4', count: 1, max_severity: 0.6 },
    { key: 'P', count: 1, max_severity: 0.3 },
  ],
  by_kind: [
    { key: 'military_exercise', count: 1, max_severity: 0.6 },
    { key: 'hazard', count: 1, max_severity: 0.3 },
  ],
  notable: [
    liveEvent({
      id: 'w1',
      category: 'maritime',
      subtype: 'navarea_warning',
      title: 'NAVAREA 4 2026/1: GUNNERY EXERCISE',
      point: { lon: -76.5, lat: 39.2 },
      severity: 0.6,
      url: 'https://msi.nga.mil/NavWarnings?navArea=4',
    }),
  ],
  latest: [],
};

export const spaceBoard: SpaceBoard = {
  stations: [
    liveEvent({
      id: 'iss',
      category: 'space',
      subtype: 'satellite',
      title: 'ISS (ZARYA)',
      point: { lon: 10, lat: 20 },
      attributes: { altitude_km: 420.3, speed_km_s: 7.66 },
    }),
  ],
  launches: [
    liveEvent({
      id: 'l1',
      category: 'space',
      subtype: 'launch',
      title: 'Launch: Spectrum',
      point: { lon: 15.6, lat: 69.1 },
      attributes: { net: '2026-09-05T20:00:00+00:00' },
    }),
  ],
  kp: 5.33,
  kp_level: 'storm',
  alerts_24h: 1,
  latest_alerts: [],
};

export const cyberBoard: CyberBoard = {
  outages_24h: 1,
  outages_by_country: [{ key: 'TN', count: 1, max_severity: 0.8 }],
  ransomware_7d: 1,
  ransomware_by_country: [{ key: 'US', count: 1, max_severity: 0.5 }],
  ransomware_by_group: [{ key: 'akira', count: 1, max_severity: 0.5 }],
  kev_7d: 1,
  latest_outages: [],
  latest_claims: [],
  latest_kev: [
    liveEvent({
      id: 'k1',
      category: 'cyber',
      subtype: 'kev',
      title: 'CVE-2026-0001 added to KEV',
      point: null,
      url: null,
    }),
  ],
};
