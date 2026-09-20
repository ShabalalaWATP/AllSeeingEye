import { screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import type { JamCell } from '@/lib/api/aviation';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';
import { mockWebGl2 } from '@/test/env';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));
beforeEach(() => {
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
});
interface JamLayer {
  id: string;
  props: { data: JamCell[]; getLineWidth: (cell: JamCell) => number };
}
function jamLayer() {
  return (MapboxOverlay.instances[0]?.props.layers as JamLayer[] | undefined)?.find(
    (layer) => layer.id === 'gnss-interference',
  );
}
const red: JamCell = {
  lon: 5.5,
  lat: 50.5,
  size: 1,
  good: 5,
  bad: 5,
  percent_bad: 40,
  level: 'red',
};
const amber: JamCell = {
  lon: 6.5,
  lat: 51.5,
  size: 1,
  good: 23,
  bad: 2,
  percent_bad: 4,
  level: 'amber',
};

it.each(['globe', 'map'] as const)(
  'offers independent GNSS filtering, locating and selection on the %s',
  async (mode) => {
    const fetch = vi.fn(() =>
      HttpResponse.json({
        cells: [red, amber],
        updated_at: new Date().toISOString(),
        limited: false,
      }),
    );
    server.use(http.get('/api/trackers/aviation/jamming', fetch));
    useGlobeStore.setState({ mode, interference: false });
    useEventsStore.setState({ hidden: ['aviation'], windowHours: 1 });
    const { user } = renderApp('/', 'user');
    await user.click(await screen.findByRole('button', { name: 'Cyber filters' }));
    await user.click(screen.getByRole('button', { name: 'GPS interference' }));
    expect(screen.getByText(/GPS interference is off/)).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
    await user.click(screen.getByRole('switch', { name: 'GPS interference 0' }));
    await waitFor(() => expect(jamLayer()?.props.data).toHaveLength(2));
    expect(useEventsStore.getState().hidden).toContain('aviation');
    expect(fetch).toHaveBeenCalledOnce();
    await user.click(screen.getByRole('button', { name: 'Locate GNSS cell 50.5, 5.5' }));
    expect(FakeMap.instances[0]!.flyTo).toHaveBeenLastCalledWith({ center: [5.5, 50.5], zoom: 6 });
    expect(jamLayer()?.props.getLineWidth(red)).toBe(2);
    const details = screen.getByRole('complementary', { name: 'Map details' });
    expect(within(details).getByText('5 poor; 5 good')).toBeInTheDocument();
    await user.click(within(details).getByRole('button', { name: 'Close map details' }));
    expect(jamLayer()?.props.getLineWidth(red)).toBe(0);
    await user.click(screen.getByRole('radio', { name: 'Red only' }));
    expect(jamLayer()?.props.data).toEqual([red]);
    expect(screen.getByRole('switch', { name: 'GPS interference 1' })).toBeChecked();
    await user.click(screen.getByRole('switch', { name: 'GPS interference 1' }));
    expect(jamLayer()).toBeUndefined();
  },
);

it('keeps shared time and appearance controls on the right without duplicating layer switches', async () => {
  const { user } = renderApp('/', 'user');
  await screen.findByRole('button', { name: 'Tools' });
  const tools = screen.getByRole('group', { name: 'Map tools' });
  const layers = screen.getByRole('group', { name: 'Map layers' });
  expect(within(tools).queryByRole('button', { name: 'Event time' })).not.toBeInTheDocument();
  expect(within(layers).queryByRole('button', { name: 'Event time' })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Topics & time' })).not.toBeInTheDocument();
  await openMapTool(user, 'Event time');
  const filters = screen.getByRole('region', { name: 'Event time' });
  expect(filters).toHaveAttribute('data-side', 'right');
  expect(within(filters).queryByRole('switch')).not.toBeInTheDocument();
  expect(within(filters).getByRole('radiogroup', { name: 'Time window' })).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Layers and settings' })).not.toBeInTheDocument();
  await user.click(within(tools).getByRole('button', { name: 'Tools' }));
  const chooser = screen.getByRole('region', { name: 'Tools' });
  expect(
    within(chooser).getByRole('button', { name: 'British National Grid' }),
  ).toBeInTheDocument();
  await user.click(within(chooser).getByRole('button', { name: 'Map style' }));
  expect(screen.queryByRole('region', { name: 'Event time' })).not.toBeInTheDocument();
  const style = screen.getByRole('region', { name: 'Map style' });
  expect(within(style).getByRole('switch', { name: 'Day and night' })).toBeInTheDocument();
  expect(within(style).getByRole('switch', { name: 'Reduce graphics load' })).toBeInTheDocument();
  await user.click(within(style).getByRole('radio', { name: 'Streets' }));
  expect(useGlobeStore.getState().baseLayer).toBe('streets');
});
import { openMapTool } from '@/test/mapTools';
