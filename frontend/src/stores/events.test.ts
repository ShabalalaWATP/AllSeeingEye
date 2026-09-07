import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';

import { liveEvent } from '@/test/fixtures';
import { server } from '@/test/server';

import {
  MAX_CLIENT_EVENTS,
  countByCategory,
  filterByCountry,
  filterByWindow,
  initialEventsState,
  selectCountryEvents,
  selectSelectedEvent,
  selectVisibleEvents,
  useEventsStore,
} from './events';

describe('events store', () => {
  beforeEach(() => {
    useEventsStore.setState({ ...initialEventsState });
  });

  it('keeps unknown publication dates last and out of publication-window filters', () => {
    const undated = liveEvent({ id: 'undated', published_at: null });
    const dated = liveEvent({ id: 'dated' });
    useEventsStore.getState().applyUpsert([undated, dated]);
    expect(useEventsStore.getState().list.map((event) => event.id)).toEqual(['dated', 'undated']);
    const now = Date.parse(dated.published_at!);
    expect(filterByWindow([undated, dated], 24, now)).toEqual([dated]);
    expect(filterByWindow([undated], null, now)).toEqual([undated]);
  });

  it('loads events and stats from the API', async () => {
    server.use(
      http.get('/api/events', () =>
        HttpResponse.json({
          items: [liveEvent(), liveEvent({ id: 'e2', category: 'cyber', point: null })],
          count: 2,
        }),
      ),
      http.get('/api/events/stats', () =>
        HttpResponse.json({ total: 2, estimated_bytes: 100, budget_bytes: 1000, per_category: [] }),
      ),
    );
    await useEventsStore.getState().load();
    const state = useEventsStore.getState();
    expect(state.loaded).toBe(true);
    expect(state.list.map((e) => e.id)).toEqual(['e1', 'e2']);
    expect(state.stats?.total).toBe(2);
    expect(countByCategory(state.list)).toEqual({ disaster: 1, cyber: 1 });
  });

  it('records a load failure', async () => {
    server.use(
      http.get('/api/events', () =>
        HttpResponse.json({ error: { code: 'x', message: 'Down.' } }, { status: 500 }),
      ),
    );
    await useEventsStore.getState().load();
    expect(useEventsStore.getState().error).toBe('Down.');
    expect(useEventsStore.getState().loaded).toBe(true);
  });

  it('applies stream upserts and expiries and keeps the selection valid', () => {
    const store = useEventsStore.getState();
    store.handleStreamMessage({
      event: 'event.upsert',
      data: JSON.stringify({
        source_id: 's',
        events: [liveEvent(), liveEvent({ id: 'e2', published_at: '2026-09-06T00:00:00Z' })],
      }),
      id: null,
    });
    expect(useEventsStore.getState().list.map((e) => e.id)).toEqual(['e2', 'e1']);
    useEventsStore.getState().select('e1');
    expect(selectSelectedEvent(useEventsStore.getState())?.id).toBe('e1');
    useEventsStore.getState().handleStreamMessage({
      event: 'event.expire',
      data: JSON.stringify({ ids: ['e1'], count: 1 }),
      id: null,
    });
    expect(useEventsStore.getState().list.map((e) => e.id)).toEqual(['e2']);
    expect(useEventsStore.getState().selectedId).toBeNull();
    useEventsStore
      .getState()
      .handleStreamMessage({ event: 'event.upsert', data: 'not json', id: null });
    useEventsStore
      .getState()
      .handleStreamMessage({ event: 'event.upsert', data: '{"events":"bad"}', id: null });
    useEventsStore.getState().applyUpsert([]);
    useEventsStore.getState().applyExpire([]);
    expect(useEventsStore.getState().list).toHaveLength(1);
  });

  it('hides categories and reports status', () => {
    useEventsStore.getState().applyUpsert([liveEvent(), liveEvent({ id: 'k', category: 'cyber' })]);
    useEventsStore.getState().toggleCategory('cyber');
    expect(selectVisibleEvents(useEventsStore.getState()).map((e) => e.id)).toEqual(['e1']);
    useEventsStore.getState().toggleCategory('cyber');
    expect(selectVisibleEvents(useEventsStore.getState())).toHaveLength(2);
    useEventsStore.getState().setStatus('live');
    expect(useEventsStore.getState().status).toBe('live');
    useEventsStore.getState().reset();
    expect(useEventsStore.getState().list).toEqual([]);
  });

  it('scopes the mirror to one nation before the category switches apply', () => {
    const german = liveEvent({ id: 'de', country_iso: 'DE' });
    const british = liveEvent({ id: 'gb', country_iso: 'GB', category: 'cyber' });
    const nowhere = liveEvent({ id: 'no', country_iso: null });
    useEventsStore.getState().applyUpsert([german, british, nowhere]);
    expect(filterByCountry([german, british], null)).toEqual([german, british]);
    useEventsStore.getState().setCountry('GB');
    expect(selectCountryEvents(useEventsStore.getState()).map((e) => e.id)).toEqual(['gb']);
    useEventsStore.getState().toggleCategory('cyber');
    expect(selectVisibleEvents(useEventsStore.getState())).toEqual([]);
    useEventsStore.getState().setCountry(null);
    expect(selectVisibleEvents(useEventsStore.getState()).map((e) => e.id)).toEqual(['de', 'no']);
  });

  it('bounds the client mirror by dropping the oldest observed events', () => {
    const many = Array.from({ length: MAX_CLIENT_EVENTS + 5 }, (_, index) =>
      liveEvent({
        id: `m${index}`,
        observed_at: new Date(Date.UTC(2026, 8, 5, 0, index)).toISOString(),
      }),
    );
    useEventsStore.getState().applyUpsert(many);
    expect(useEventsStore.getState().list).toHaveLength(MAX_CLIENT_EVENTS);
    useEventsStore
      .getState()
      .applyUpsert([liveEvent({ id: 'newest', observed_at: '2027-01-01T00:00:00Z' })]);
    const state = useEventsStore.getState();
    expect(Object.keys(state.byId).length).toBe(MAX_CLIENT_EVENTS);
    expect(state.byId.m0).toBeUndefined();
    expect(state.byId.newest).toBeDefined();
  });
});
