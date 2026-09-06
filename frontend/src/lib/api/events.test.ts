import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { ADMIN_TOKEN, adminUser, tokenFor } from '@/test/fixtures';
import { server } from '@/test/server';
import { useAuthStore } from '@/stores/auth';

import { eventsQueryString, fetchEvents, fetchSources, resetSource } from './events';

const health = {
  source_id: 'usgs_earthquakes',
  status: 'healthy',
  last_success: '2026-09-05T00:00:00Z',
  last_error: null,
  last_error_at: null,
  consecutive_failures: 0,
  items_last_poll: 12,
  last_latency_ms: 210,
  next_poll_at: '2026-09-05T00:05:00Z',
  polls: 3,
};

const source = {
  id: 'usgs_earthquakes',
  name: 'USGS earthquakes',
  organisation: 'USGS',
  category: 'disaster',
  kind: 'geojson',
  url: 'https://earthquake.usgs.gov/feed.geojson',
  reliability: 'A',
  poll_interval_seconds: 300,
  language: 'en',
  licence_note: 'Public domain',
  homepage: 'https://earthquake.usgs.gov',
  requires_key: false,
  instrument: true,
  flags: [],
  health,
};

describe('events api', () => {
  it('builds query strings only from the fields given', () => {
    expect(eventsQueryString({})).toBe('');
    expect(
      eventsQueryString({
        categories: ['disaster', 'cyber'],
        bbox: [-10, 35, 5, 60],
        country: 'GB',
        since: '2026-09-04T00:00:00Z',
        limit: 50,
      }),
    ).toBe(
      '?categories=disaster%2Ccyber&bbox=-10%2C35%2C5%2C60&country=GB&since=2026-09-04T00%3A00%3A00Z&limit=50',
    );
    expect(eventsQueryString({ categories: [] })).toBe('');
  });

  it('passes the query through and unwraps the items', async () => {
    let seen = '';
    server.use(
      http.get('/api/events', ({ request }) => {
        seen = new URL(request.url).search;
        return HttpResponse.json({ items: [], count: 0 });
      }),
    );
    useAuthStore.getState().setSession(tokenFor(adminUser));
    await expect(fetchEvents({ limit: 5 })).resolves.toEqual([]);
    expect(seen).toBe('?limit=5');
  });

  it('lists sources and resets one as an admin', async () => {
    let authorisation: string | null = null;
    let resetPath = '';
    server.use(
      http.get('/api/admin/sources', ({ request }) => {
        authorisation = request.headers.get('Authorization');
        return HttpResponse.json({ items: [source] });
      }),
      http.post('/api/admin/sources/:id/reset', ({ request, params }) => {
        resetPath = new URL(request.url).pathname;
        return HttpResponse.json({ ...health, source_id: String(params.id) });
      }),
    );
    useAuthStore.getState().setSession(tokenFor(adminUser));
    const sources = await fetchSources();
    expect(sources[0]?.name).toBe('USGS earthquakes');
    expect(authorisation).toBe(`Bearer ${ADMIN_TOKEN}`);
    // The id is escaped on the way out and decoded by the server.
    const reset = await resetSource('gdacs rss');
    expect(resetPath).toBe('/api/admin/sources/gdacs%20rss/reset');
    expect(reset.source_id).toBe('gdacs rss');
  });
});
