import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it, vi } from 'vitest';
import type { Layer } from '@deck.gl/core';
import { mockWebGl2 } from '@/test/env';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeMap } from '@/test/fakeMap';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

// Resolve the lazy route before timed UI assertions, including on a cold test worker.
import './GlobePage';

beforeEach(() => {
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
});

function layer(id: string): Layer | undefined {
  const layers = MapboxOverlay.instances[0]?.props.layers as Layer[] | undefined;
  return layers?.find((item) => item.id === id);
}
function clickMap(lon: number, lat: number) {
  act(() => FakeMap.instances[0]?.fire('click', { lngLat: { lng: lon, lat } }));
}

it('opens Space, Natural hazards and Conflict filters beneath their left category controls', async () => {
  const { user } = renderApp('/', 'user');
  await screen.findByRole('region', { name: '3D globe' });
  const rail = screen.getByRole('group', { name: 'Map layers' });
  const right = screen.getByRole('group', { name: 'Map tools' });
  expect(
    within(right).queryByRole('button', {
      name: /Satellite filters|Space filters|Natural hazard filters|Conflict report filters/,
    }),
  ).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Satellite filters' })).not.toBeInTheDocument();
  await user.click(within(rail).getByRole('button', { name: 'Space filters' }));
  expect(screen.getByRole('region', { name: 'Space' })).toHaveAttribute('data-side', 'left');
  expect(screen.getByRole('radiogroup', { name: 'Satellite catalogue' })).toBeVisible();
  await user.click(within(rail).getByRole('button', { name: 'Natural hazard filters' }));
  expect(screen.getByRole('region', { name: 'Natural hazards' })).toHaveAttribute(
    'data-side',
    'left',
  );
  expect(screen.getByLabelText('Earthquake minimum magnitude')).toBeVisible();
  expect(screen.queryByRole('radiogroup', { name: 'Satellite catalogue' })).not.toBeInTheDocument();
  await user.click(within(rail).getByRole('button', { name: 'Conflict report filters' }));
  expect(screen.getByRole('region', { name: 'Conflict reports' })).toHaveAttribute(
    'data-side',
    'left',
  );
  expect(screen.getByRole('region', { name: 'Conflict report filters' })).toBeVisible();
});

it('gives clicks to one drawing tool, retains sketches across projection changes and stops on close', async () => {
  const { user } = renderApp('/', 'user');
  await screen.findByRole('region', { name: '3D globe' });
  await user.click(screen.getByRole('button', { name: 'Measure distance and area' }));
  await user.click(screen.getByRole('button', { name: 'Pick points on map' }));
  clickMap(0, 0);
  expect(layer('measurement-points')?.props.data).toHaveLength(1);
  await user.click(screen.getByRole('button', { name: 'Draw on map' }));
  await user.click(screen.getByRole('button', { name: 'Path' }));
  await user.click(screen.getByRole('button', { name: 'Draw with map clicks' }));
  clickMap(1, 1);
  clickMap(2, 2);
  expect(layer('measurement-points')?.props.data).toHaveLength(1);
  expect(layer('drawing-measurement-points')?.props.data).toHaveLength(2);
  const mode = screen.getByRole('group', { name: 'View mode' });
  await user.click(within(mode).getByRole('button', { name: 'Map' }));
  expect(layer('drawing-measurement-points')?.props.data).toHaveLength(2);
  await user.click(within(mode).getByRole('button', { name: 'Globe' }));
  expect(layer('drawing-measurement-points')?.props.data).toHaveLength(2);
  await user.click(screen.getByRole('button', { name: 'Close tool' }));
  clickMap(3, 3);
  expect(layer('drawing-measurement-points')?.props.data).toHaveLength(2);
  expect(screen.getByRole('button', { name: 'Draw on map' })).toHaveFocus();
  await user.click(screen.getByRole('button', { name: 'Measure distance and area' }));
  await user.click(screen.getByRole('button', { name: 'Pick points on map' }));
  clickMap(4, 4);
  expect(layer('measurement-points')?.props.data).toHaveLength(2);
  expect(layer('drawing-measurement-points')?.props.data).toHaveLength(2);
});

it('creates an unpickable route layer only after Calculate and removes it on Clear', async () => {
  const calculate = vi.fn();
  server.use(
    http.get('/api/navigation/capabilities', () =>
      HttpResponse.json({
        provider: 'FOSSGIS Valhalla',
        operator_contact: 'operator@example.com',
        available: true,
        configuration_message: null,
        privacy: 'Coordinates sent only on Calculate.',
      }),
    ),
    http.post('/api/navigation/route', () => {
      calculate();
      return HttpResponse.json({
        mode: 'driving',
        distance_km: 2,
        duration_seconds: 300,
        coordinates: [
          [0, 0],
          [0.01, 0.01],
        ],
        steps: [{ instruction: 'Continue ahead', distance_km: 2, duration_seconds: 300 }],
        provider: 'FOSSGIS Valhalla',
        attribution: 'OpenStreetMap',
        limitations: 'Planning estimate only.',
      });
    }),
  );
  const { user } = renderApp('/', 'user');
  await screen.findByRole('region', { name: '3D globe' });
  await user.click(screen.getByRole('button', { name: 'Route planner' }));
  await screen.findByRole('link', { name: 'operator@example.com' });
  for (const [index, value] of [
    [1, '0'],
    [2, '0.01'],
  ] as const) {
    for (const axis of ['latitude', 'longitude']) {
      const input = screen.getByRole('textbox', { name: `Waypoint ${index} ${axis}` });
      await user.clear(input);
      await user.type(input, value);
    }
  }
  expect(calculate).not.toHaveBeenCalled();
  expect(layer('navigation-route')).toBeUndefined();
  await user.click(screen.getByRole('button', { name: 'Calculate route' }));
  await waitFor(() => expect(layer('navigation-route')).toBeDefined());
  expect(layer('navigation-route')?.props.pickable).toBe(false);
  expect(calculate).toHaveBeenCalledOnce();
  await user.click(screen.getByRole('button', { name: 'Clear route' }));
  expect(layer('navigation-route')).toBeUndefined();
});
