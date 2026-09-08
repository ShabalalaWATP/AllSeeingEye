import { act, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { renderApp } from '@/test/render';
import { mockWebGl2 } from '@/test/env';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { server } from '@/test/server';
import { liveEvent } from '@/test/fixtures';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';
import type { Camera } from '@/lib/api/cameras';
vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));
const camera: Camera = {
  id: 'tfl-test',
  provider: 'tfl',
  title: 'Test public road camera',
  latitude: 51.5,
  longitude: -0.1,
  snapshot_url: 'https://s3-eu-west-1.amazonaws.com/jamcams.tfl.gov.uk/00001.00100.jpg',
  source_url: 'https://tfl.gov.uk/traffic/status/',
  attribution: 'Transport for London',
  captured_at: null,
  coordinate_precision: 'exact',
};
function layers() {
  return (MapboxOverlay.instances[0]?.props.layers ?? []) as {
    id: string;
    props: { onClick: (info: { object: Camera }) => void };
  }[];
}
beforeEach(async () => {
  // Test map interactions independently of the cold lazy-route transform time.
  await import('./GlobePage');
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
  server.use(
    http.get('/api/cameras', () =>
      HttpResponse.json({
        cameras: [camera],
        providers: [
          {
            id: 'tfl',
            name: 'Transport for London',
            status: 'available',
            count: 1,
            fetched_at: '2026-09-08T09:00:00Z',
            message: null,
          },
        ],
        fetched_at: '2026-09-08T09:00:00Z',
      }),
    ),
  );
});
it.each(['globe', 'map'] as const)(
  'selects and clears camera highlights on the %s',
  async (mode) => {
    useGlobeStore.setState({ mode });
    const { user } = renderApp('/', 'user');
    await user.click(await screen.findByRole('button', { name: 'CCTV' }));
    await user.click(screen.getByRole('switch', { name: /Show public cameras/ }));
    await waitFor(() =>
      expect(layers().find((item) => item.id === 'public-camera-icons')).toBeDefined(),
    );
    act(() => {
      layers()
        .find((item) => item.id === 'public-camera-icons')!
        .props.onClick({ object: camera });
    });
    expect(screen.getByRole('complementary', { name: 'Map details' })).toHaveTextContent(
      camera.title,
    );
    expect(layers().find((item) => item.id === 'selected-camera-halo')).toBeDefined();
    await user.click(
      within(screen.getByRole('complementary', { name: 'Map details' })).getByRole('button', {
        name: /Close/,
      }),
    );
    expect(layers().find((item) => item.id === 'selected-camera-halo')).toBeUndefined();
    await user.click(screen.getByRole('button', { name: camera.title }));
    expect(layers().find((item) => item.id === 'selected-camera-halo')).toBeDefined();
    act(() => {
      const event = liveEvent({
        id: 'camera-switch-event',
        category: 'news',
        title: 'Other map record',
      });
      useEventsStore.getState().applyUpsert([event]);
    });
    await user.click(screen.getByRole('button', { name: /Other map record/ }));
    expect(layers().find((item) => item.id === 'selected-camera-halo')).toBeUndefined();
    expect(screen.getByRole('complementary', { name: 'Event details' })).toHaveTextContent(
      'Other map record',
    );
    await user.click(screen.getByRole('button', { name: camera.title }));
    expect(screen.queryByRole('complementary', { name: 'Event details' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('switch', { name: /Show public cameras/ }));
    expect(layers().find((item) => item.id === 'public-camera-icons')).toBeUndefined();
    expect(screen.queryByRole('complementary', { name: 'Map details' })).not.toBeInTheDocument();
  },
);
