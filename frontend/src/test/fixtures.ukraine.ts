import type { UkraineBoard, UkraineControl } from '@/lib/api/ukraine';

import { liveEvent } from './fixtures.events';

const totals = {
  personnel_units: 1506900,
  tanks: 12344,
  armoured_fighting_vehicles: 25330,
  artillery_systems: 49678,
  uav_systems: 514317,
  cruise_missiles: 5111,
};

export const controlSummary: UkraineBoard['control'] = {
  assessment_date: '2026-09-13',
  release_stamp: '20260913044905332209',
  retrieved_at: '2026-09-13T21:18:00Z',
  attribution: 'Zhukov and Ayers (2023). VIINA 2.0. Harvard University.',
  licence: 'ODbL 1.0',
  source_url: 'https://github.com/zhukovyuri/VIINA',
  method_note: 'Majority vote of public maps; a reported line, not observed positions.',
  places_total: 33141,
  retained: 3,
  counts: { ua: 27197, ru: 5892, contested: 52, unknown: 0 },
  oblasts: [
    { name: "Donets'k", total: 2000, ua: 570, ru: 1430, contested: 20, unknown: 0 },
    { name: 'Kyiv', total: 1500, ua: 1500, ru: 0, contested: 0, unknown: 0 },
  ],
  changes: [
    {
      geoname_id: 692588,
      name: 'Stepanivka',
      oblast: "Donets'k",
      previous: 'ua',
      status: 'ru',
      changed_on: '2026-09-13',
    },
  ],
};

export const ukraineBoard: UkraineBoard = {
  generated_at: '2026-09-13T22:00:00Z',
  day_number: 1663,
  day_basis: 'claimed',
  window_days: 14,
  events_scanned: 3,
  updates: [
    {
      event: liveEvent({
        id: 'isw1',
        source_id: 'isw_assessments',
        category: 'conflict',
        subtype: 'assessment',
        title: 'Russian Offensive Campaign Assessment, September 12, 2026',
        summary: 'Key takeaways: advances near Pokrovsk.',
        url: 'https://understandingwar.org/example',
        point: null,
        country_iso: 'UA',
        tags: ['assessment'],
        reliability: 'B',
        grade: 'B3',
      }),
      group: 'assessments',
      lenses: [],
    },
    {
      event: liveEvent({
        id: 'ki1',
        source_id: 'kyiv_independent',
        category: 'news',
        subtype: 'article',
        title: 'Mobilisation rules tightened',
        summary: 'Recruits and reservists affected.',
        url: 'https://kyivindependent.com/example',
        country_iso: 'UA',
        tags: [],
        reliability: 'C',
        grade: 'C3',
      }),
      group: 'ukrainian',
      lenses: ['workforce'],
    },
    {
      event: liveEvent({
        id: 'tass1',
        source_id: 'tass_en',
        category: 'news',
        subtype: 'article',
        title: 'Ministry reports drone interceptions over Belgorod',
        summary: null,
        url: 'https://tass.com/example',
        country_iso: 'RU',
        tags: ['state_controlled'],
        reliability: 'C',
        grade: 'C5',
      }),
      group: 'russian',
      lenses: ['equipment', 'strikes'],
    },
  ],
  lens_counts: { equipment: 1, strikes: 1, workforce: 1 },
  claims: [
    {
      reported_on: '2026-09-12',
      day: 1662,
      source_url: 'https://www.facebook.com/GeneralStaff.ua/posts/previous',
      totals: { ...totals, tanks: 12342 },
      increase: { tanks: 4, personnel_units: 1310 },
    },
    {
      reported_on: '2026-09-13',
      day: 1663,
      source_url: 'https://www.facebook.com/GeneralStaff.ua/posts/example',
      totals,
      increase: { tanks: 2, personnel_units: 1520 },
    },
  ],
  categories: {
    personnel_units: 'Personnel',
    tanks: 'Tanks',
    armoured_fighting_vehicles: 'Armoured fighting vehicles',
    artillery_systems: 'Artillery systems',
    uav_systems: 'Drones',
    cruise_missiles: 'Cruise missiles',
  },
  headline_categories: [
    'personnel_units',
    'tanks',
    'armoured_fighting_vehicles',
    'artillery_systems',
    'uav_systems',
    'cruise_missiles',
  ],
  control: controlSummary,
  freshness: {
    control_assessed: '2026-09-13',
    assessment_published: '2026-09-13T01:38:00Z',
    claim_reported: '2026-09-13',
    latest_update: '2026-09-13T20:00:00Z',
  },
};

const square = [
  [
    [37.0, 48.0],
    [37.2, 48.0],
    [37.2, 48.2],
    [37.0, 48.2],
    [37.0, 48.0],
  ],
];

export const ukraineControl: UkraineControl = {
  summary: controlSummary,
  settlements: [
    {
      geoname_id: 1,
      name: 'Pokrovsk',
      oblast: "Donets'k",
      lat: 48.28,
      lon: 37.17,
      status: 'contested',
      since: '2026-08-30',
      votes: ['contested', 'contested', 'ru', 'unknown'],
    },
    {
      geoname_id: 2,
      name: 'Stepanivka',
      oblast: "Donets'k",
      lat: 48.1,
      lon: 37.1,
      status: 'ru',
      since: '2026-09-13',
      votes: ['ru', 'ru', 'ru', 'unknown'],
    },
    {
      geoname_id: 3,
      name: 'Dobropillia',
      oblast: "Donets'k",
      lat: 48.47,
      lon: 37.08,
      status: 'ua',
      since: null,
      votes: ['ua', 'ua', 'ua', 'unknown'],
    },
  ],
  areas: [
    { status: 'ru', polygons: [square] },
    { status: 'contested', polygons: [] },
  ],
  outlines: [{ name: 'Donetsk Oblast', iso: 'UA-14', polygons: [square] }],
};
