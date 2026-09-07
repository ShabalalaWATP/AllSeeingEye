import { act, screen, waitFor, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { renderApp } from '@/test/render';
import { mockWebGl2 } from '@/test/env';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/mapbox', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

it('keeps typed measurement available while disabling picking without WebGL', async () => {
  FakeMap.reset();
  MapboxOverlay.reset();
  mockWebGl2(false);
  renderApp('/', 'user');
  expect(await screen.findByRole('button', { name: 'Pick points on map' })).toBeDisabled();
  expect(screen.getByLabelText('Longitude')).toBeEnabled();
});

it('picks only when enabled, preserves vertices across projection changes and clears its layers', async () => {
  FakeMap.reset();
  MapboxOverlay.reset();
  mockWebGl2(true);
  const { user } = renderApp('/', 'user');
  const panel = await screen.findByRole('region', { name: 'Map measurement' });
  await waitFor(() => expect(FakeMap.instances).toHaveLength(1));
  const map = FakeMap.instances[0]!;
  act(() => map.fire('click', { lngLat: { lng: 0, lat: 0 } }));
  expect(within(panel).getByText('0/32 points')).toBeInTheDocument();
  await user.click(within(panel).getByRole('button', { name: 'Pick points on map' }));
  act(() => {
    map.fire('click', { lngLat: { lng: 0, lat: 0 } });
    map.fire('click', { lngLat: { lng: 1, lat: 0 } });
    map.fire('click', { lngLat: { lng: NaN, lat: 0 } });
  });
  expect(within(panel).getByLabelText('Measurement result')).toHaveTextContent('111.319 km');
  await user.click(
    within(screen.getByRole('group', { name: 'View mode' })).getByRole('button', { name: 'Map' }),
  );
  expect(FakeMap.instances).toHaveLength(1);
  expect(within(panel).getByText('2/32 points')).toBeInTheDocument();
  await user.click(within(panel).getByRole('button', { name: 'Clear measure' }));
  const layers = MapboxOverlay.instances[0]!.props.layers as { id: string }[];
  expect(layers.some((layer) => layer.id.startsWith('measurement-'))).toBe(false);
  expect(layers.some((layer) => layer.id.startsWith('events-'))).toBe(true);
});
