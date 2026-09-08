import { act, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeAll, beforeEach, expect, it, vi } from 'vitest';
import { useEventsStore } from '@/stores/events';
import { mockWebGl2 } from '@/test/env';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeMap } from '@/test/fakeMap';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { liveEvent } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

beforeEach(() => {
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
});

// Resolve the real lazy route before timing mounted stream behaviour.
beforeAll(async () => {
  await import('./GlobePage');
});

it('an actual mounted stream callback clears an expired selection and reloads the map', async () => {
  mockWebGl2(true);
  renderApp('/', 'user');
  await waitFor(() => expect(useEventsStore.getState().loaded).toBe(true));
  const stale = liveEvent({ id: 'stale-vessel', category: 'maritime', subtype: 'vessel_position' });
  act(() => {
    useEventsStore.getState().applyUpsert([stale]);
    useEventsStore.getState().select(stale.id);
  });
  expect(screen.getByRole('complementary', { name: 'Event details' })).toBeInTheDocument();
  const fresh = liveEvent({ id: 'fresh-event', title: 'Fresh snapshot record' });
  server.use(http.get('/api/events', () => HttpResponse.json({ items: [fresh], count: 1 })));
  act(() => {
    FakeEventStreamClient.instances[0]?.emit({
      event: 'event.resync',
      data: '{"reason":"expiry_overflow"}',
      id: null,
    });
  });
  expect(screen.queryByRole('complementary', { name: 'Event details' })).not.toBeInTheDocument();
  expect(useEventsStore.getState().byId[stale.id]).toBeUndefined();
  await waitFor(() =>
    expect(useEventsStore.getState().list.map((event) => event.id)).toEqual([fresh.id]),
  );
});
