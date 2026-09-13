import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it, vi } from 'vitest';
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

const aircraft = liveEvent({
  id: 'plane',
  category: 'aviation',
  subtype: 'aircraft',
  title: 'EYE123',
  attributes: { callsign: 'EYE123', on_ground: false },
});
const vessel = liveEvent({
  id: 'ship',
  category: 'maritime',
  subtype: 'vessel_position',
  title: 'Survey ship',
});
function layerIds() {
  return ((MapboxOverlay.instances[0]?.props.layers as { id: string }[] | undefined) ?? []).map(
    (layer) => layer.id,
  );
}
beforeEach(() => {
  mockWebGl2(true);
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  server.use(http.get('/api/trackers/conflicts', () => HttpResponse.json({ items: [] })));
});

it('uses one drawer and keeps aircraft search separate from boats until it is cleared', async () => {
  // Layer changes may refresh the snapshot. Keep test traffic in that source as well
  // as stream updates so a legitimate refresh cannot race away these fixtures.
  server.use(
    http.get('/api/events', () => HttpResponse.json({ items: [aircraft, vessel], count: 2 })),
  );
  const { user } = renderApp('/', 'user');
  // The first render loads the lazy globe and its tool modules. Coverage instrumentation
  // can exceed the shared four-second wait before the controls are mounted.
  await screen.findByRole('button', { name: 'Flight filters' }, { timeout: 10_000 });
  act(() => useEventsStore.getState().applyUpsert([aircraft, vessel]));
  const flights = screen.getByRole('button', { name: 'Flight filters' });
  await user.click(flights);
  await user.type(screen.getByRole('searchbox', { name: 'Search aircraft' }), 'EYE123');
  await user.click(screen.getByRole('button', { name: 'Boat list' }));
  expect(screen.queryByRole('region', { name: 'Flight filters' })).not.toBeInTheDocument();
  expect(screen.getByRole('searchbox', { name: 'Search vessels' })).toHaveValue('');
  expect(screen.getByRole('button', { name: /Survey ship/ })).toBeInTheDocument();
  await user.click(flights);
  expect(screen.getByRole('searchbox', { name: 'Search aircraft' })).toHaveValue('EYE123');
  await user.keyboard('{Escape}');
  expect(flights).toHaveFocus();
  // The refinement lives in its panel; clearing the field is the reset.
  await user.click(flights);
  await user.clear(screen.getByRole('searchbox', { name: 'Search aircraft' }));
  expect(screen.getByRole('searchbox', { name: 'Search aircraft' })).toHaveValue('');
});

it('fetches context only when requested and locates a selected warning outside the viewport store', async () => {
  const reads: URL[] = [];
  const warning = liveEvent({
    id: 'warning',
    category: 'maritime',
    source_id: 'nga_navarea',
    title: 'Navigation exercise notice',
    point: { lon: 22, lat: 33 },
    attributes: { nav_area: 'IV', positions: 2 },
  });
  server.use(
    http.get('/api/events', ({ request }) => {
      const url = new URL(request.url);
      if (url.searchParams.get('sources') === 'nga_navarea') reads.push(url);
      return HttpResponse.json({
        items: url.searchParams.get('sources') === 'nga_navarea' ? [warning] : [],
        count: url.searchParams.get('sources') === 'nga_navarea' ? 1 : 0,
      });
    }),
  );
  const { user } = renderApp('/', 'user');
  await screen.findByRole('button', { name: 'Boat list' });
  expect(reads).toHaveLength(0);
  await user.click(screen.getByRole('button', { name: 'Boat list' }));
  expect(reads).toHaveLength(0);
  await user.click(screen.getByRole('button', { name: 'Navigation warnings' }));
  await screen.findByText('Navigation exercise notice');
  expect(reads).toHaveLength(1);
  expect(reads[0]?.searchParams.get('limit')).toBe('100');
  expect(reads[0]?.searchParams.has('bbox')).toBe(false);
  await user.click(screen.getByRole('button', { name: 'Locate first position' }));
  expect(FakeMap.instances[0]?.flyTo).toHaveBeenLastCalledWith({ center: [22, 33], zoom: 5 });
  expect(screen.getByRole('complementary', { name: 'Event details' })).toHaveTextContent(
    'Navigation exercise notice',
  );
  expect(useEventsStore.getState().list.find((item) => item.id === 'warning')).toBeUndefined();
  expect(layerIds()).toContain('context-selected-position');
  await user.click(
    within(screen.getByRole('complementary', { name: 'Event details' })).getByRole('button', {
      name: /close/i,
    }),
  );
  expect(layerIds()).not.toContain('context-selected-position');
  expect(reads).toHaveLength(1);
});

it('satellite list selection enables Space, then clearing details clears the selected marker', async () => {
  const { user } = renderApp('/', 'user');
  await screen.findByRole('button', { name: 'Space filters' });
  const satellite = liveEvent({
    id: 'sat',
    category: 'space',
    subtype: 'satellite',
    title: 'SKYNET TEST',
    source_id: 'celestrak_skynet',
    published_at: new Date().toISOString(),
    attributes: { norad_id: 54321, position_at: new Date().toISOString() },
  });
  act(() => useEventsStore.getState().applyUpsert([satellite]));
  await user.click(screen.getByRole('button', { name: 'Space filters' }));
  await user.type(screen.getByRole('searchbox', { name: 'Find a satellite' }), '54321');
  await user.click(screen.getByRole('button', { name: /SKYNET TEST/ }));
  expect(useEventsStore.getState().hidden).not.toContain('space');
  await waitFor(() => expect(useEventsStore.getState().selectedId).toBe('sat'));
  expect(screen.getByRole('complementary', { name: 'Event details' })).toHaveTextContent(
    'SKYNET TEST',
  );
  expect(FakeMap.instances[0]?.flyTo).toHaveBeenLastCalledWith({
    center: [satellite.point?.lon, satellite.point?.lat],
    zoom: 4,
  });
  await user.click(
    within(screen.getByRole('complementary', { name: 'Event details' })).getByRole('button', {
      name: /close/i,
    }),
  );
  expect(useEventsStore.getState().selectedId).toBeNull();
  if (!screen.queryByRole('searchbox', { name: 'Find a satellite' }))
    await user.click(screen.getByRole('button', { name: 'Space filters' }));
  expect(screen.getByRole('searchbox', { name: 'Find a satellite' })).toHaveValue('54321');
});

it('only offers records allowed by location quality in traffic and satellite lists', async () => {
  const { user } = renderApp('/', 'user');
  await screen.findByRole('button', { name: 'Location quality' });
  act(() =>
    useEventsStore.getState().applyUpsert([
      aircraft,
      liveEvent({
        id: 'sat-quality',
        category: 'space',
        subtype: 'satellite',
        title: 'Orbital test',
        published_at: new Date().toISOString(),
      }),
    ]),
  );
  await user.click(screen.getByRole('button', { name: 'Location quality' }));
  await user.selectOptions(
    screen.getByRole('combobox', { name: 'Show on map or globe' }),
    'approximate',
  );
  await user.click(screen.getByRole('button', { name: 'Flight filters' }));
  expect(screen.getByText('No matching aircraft loaded.')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /EYE123/ })).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Space filters' }));
  expect(screen.queryByRole('button', { name: /Orbital test/ })).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Location quality' }));
  await user.selectOptions(screen.getByRole('combobox', { name: 'Show on map or globe' }), 'all');
  await user.click(screen.getByRole('button', { name: 'Space filters' }));
  expect(screen.getByRole('button', { name: /Orbital test/ })).toBeInTheDocument();
});
