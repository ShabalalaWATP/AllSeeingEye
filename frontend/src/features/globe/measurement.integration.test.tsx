import { act, screen, waitFor, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { renderApp } from '@/test/render';
import { mockWebGl2 } from '@/test/env';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import { useEventsStore } from '@/stores/events';
// Load the real route after Vitest hoists its mocks, outside timed UI assertions.
import './GlobePage';
vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

it('keeps typed measurement available while disabling picking without WebGL', async () => {
  FakeMap.reset();
  MapboxOverlay.reset();
  mockWebGl2(false);
  const { user } = renderApp('/', 'user');
  await user.click(await screen.findByRole('button', { name: 'Measure distance and area' }));
  expect(await screen.findByRole('button', { name: 'Pick points on map' })).toBeDisabled();
  await user.click(screen.getByText('Enter coordinates manually'));
  expect(screen.getByLabelText('Longitude')).toBeVisible();
  expect(screen.getByLabelText('Longitude')).toBeEnabled();
});

it('picks only when enabled, preserves vertices across projection changes and clears its layers', async () => {
  useEventsStore.setState({ hidden: [] });
  FakeMap.reset();
  MapboxOverlay.reset();
  mockWebGl2(true);
  const { user } = renderApp('/', 'user');
  await user.click(await screen.findByRole('button', { name: 'Measure distance and area' }));
  let panel = await screen.findByRole('region', { name: 'Map measurement' });
  await waitFor(() => expect(FakeMap.instances).toHaveLength(1));
  const map = FakeMap.instances[0]!;
  act(() => map.fire('click', { lngLat: { lng: 0, lat: 0 } }));
  expect(within(panel).getByText('0/32 points')).toBeInTheDocument();
  await user.click(within(panel).getByRole('button', { name: 'Pick points on map' }));
  await waitFor(() => {
    const layers = MapboxOverlay.instances[0]!.props.layers as {
      id: string;
      props: { pickable: boolean };
    }[];
    expect(layers.find((layer) => layer.id === 'conflict-region-markers')?.props.pickable).toBe(
      false,
    );
  });
  await user.click(screen.getByRole('button', { name: 'Close tool' }));
  expect(screen.queryByRole('region', { name: 'Map measurement' })).not.toBeInTheDocument();
  act(() => {
    map.fire('click', { lngLat: { lng: 0, lat: 0 } });
    map.fire('click', { lngLat: { lng: 1, lat: 0 } });
    map.fire('click', { lngLat: { lng: NaN, lat: 0 } });
  });
  const readout = screen.getByRole('region', { name: 'Active measurement' });
  expect(readout).toHaveTextContent('111.319 km');
  expect(within(readout).getByRole('button', { name: 'Finish measuring' })).toBeVisible();
  expect(within(readout).getByRole('button', { name: 'Undo point' })).toBeEnabled();
  await user.click(screen.getByRole('button', { name: 'Measure distance and area' }));
  panel = screen.getByRole('region', { name: 'Map measurement' });
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
