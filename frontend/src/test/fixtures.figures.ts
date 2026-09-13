import type { FigureBoard, PublicFigure } from '@/lib/api/figures';

import { liveEvent } from './fixtures.events';

// A 1x1 transparent PNG stands in for a portrait; the real roster carries 64 px circles.
export const TINY_PNG =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';

export function publicFigure(overrides: Partial<PublicFigure> = {}): PublicFigure {
  return {
    id: 'ua-head-of-state',
    wikidata_id: 'Q3874799',
    name: 'Volodymyr Zelenskyy',
    office: 'President of Ukraine',
    role: 'head_of_state',
    country_iso: 'UA',
    organisation: null,
    seat_name: 'Kyiv',
    portrait: {
      png_base64: TINY_PNG,
      licence: 'CC BY 4.0',
      credit: 'President.gov.ua',
      source_url: 'https://commons.wikimedia.org/wiki/File:Example.jpg',
    },
    placement: {
      latitude: 49.99,
      longitude: 36.23,
      basis: 'reported_place',
      detail:
        'Placed by the newest geolocated report that names Volodymyr Zelenskyy. A report’s location is where the story is set, not confirmed presence.',
      event_id: 'n1',
      published_at: '2026-09-13T10:00:00Z',
    },
    mentions: 2,
    latest: [
      liveEvent({
        id: 'n1',
        category: 'news',
        subtype: 'news_report',
        title: 'Zelenskyy visits front-line troops near Kharkiv',
        point: { lon: 36.23, lat: 49.99 },
        country_iso: 'UA',
        published_at: '2026-09-13T10:00:00Z',
      }),
    ],
    ...overrides,
  };
}

export const figureBoard: FigureBoard = {
  figures: [
    publicFigure(),
    publicFigure({
      id: 'gb-head-of-government',
      wikidata_id: 'Q269909',
      name: 'Andy Burnham',
      office: 'Prime Minister of the United Kingdom',
      role: 'head_of_government',
      country_iso: 'GB',
      seat_name: 'London',
      portrait: null,
      placement: {
        latitude: 51.5,
        longitude: -0.12,
        basis: 'seat',
        detail:
          'No located reporting names Andy Burnham in this window, so the marker sits at the seat of office (London). This is a default, not an observation.',
        event_id: null,
        published_at: null,
      },
      mentions: 0,
      latest: [],
    }),
    publicFigure({
      id: 'nato',
      wikidata_id: 'Q57792',
      name: 'Mark Rutte',
      office: 'Secretary General of NATO',
      role: 'organisation',
      country_iso: null,
      organisation: 'NATO',
      seat_name: 'NATO headquarters, Brussels',
      placement: {
        latitude: 50.85,
        longitude: 4.35,
        basis: 'reported_country',
        detail:
          'Country context of the newest report that names Mark Rutte, shown at the country reference point rather than a visited place.',
        event_id: 'n2',
        published_at: '2026-09-13T08:00:00Z',
      },
      mentions: 1,
      latest: [
        liveEvent({
          id: 'n2',
          category: 'news',
          subtype: 'news_report',
          title: 'Rutte urges allies to lift spending',
          point: { lon: 4.35, lat: 50.85 },
          geo_confidence: 'country',
          country_iso: 'BE',
          published_at: '2026-09-13T08:00:00Z',
        }),
      ],
    }),
  ],
  window_hours: 72,
  events_scanned: 240,
  roster_retrieved_at: '2026-09-13T12:06:50Z',
  source_note: 'Wikidata (CC0) via the public SPARQL endpoint; portraits from Wikimedia Commons',
  generated_at: '2026-09-13T12:30:00Z',
  caveat:
    'Markers show where public reporting names an office-holder, or the seat of office when nothing located names them. Neither is confirmed presence, and absence of reporting never means an official is at home.',
};
