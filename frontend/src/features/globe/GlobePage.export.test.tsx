import { screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterEach, expect, it, vi } from 'vitest';

import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';
import { mockWebGl2 } from '@/test/env';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeMap } from '@/test/fakeMap';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { liveEvent } from '@/test/fixtures';
import { openMapTool } from '@/test/mapTools';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import './GlobePage';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

afterEach(() => vi.unstubAllGlobals());

function readBlob(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') resolve(reader.result);
      else reject(new Error('Expected text in the downloaded map.'));
    };
    reader.onerror = () => reject(new Error('Cannot read the downloaded map.'));
    reader.readAsText(blob);
  });
}

it('downloads only the loaded events selected by the current map location filter', async () => {
  useEventsStore.setState({ hidden: [] });
  useGlobeStore.setState({ opsRoom: false });
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
  const items = [
    liveEvent({ id: 'reported', title: 'Reported earthquake', geo_confidence: 'exact' }),
    liveEvent({ id: 'approximate', title: 'Approximate earthquake', geo_confidence: 'city' }),
  ];
  server.use(
    http.get('/api/events', () => HttpResponse.json({ items, count: items.length })),
    http.get('/api/trackers/conflicts', () => HttpResponse.json({ items: [] })),
  );
  const downloads: Blob[] = [];
  vi.stubGlobal(
    'URL',
    class extends URL {
      static override createObjectURL(blob: Blob) {
        downloads.push(blob);
        return 'blob:map-export';
      }
      static override revokeObjectURL() {
        return undefined;
      }
    },
  );
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);
  const { user } = renderApp('/', 'user');
  await waitFor(() => expect(useEventsStore.getState().list).toHaveLength(2));
  await openMapTool(user, 'Location quality');
  await user.selectOptions(
    screen.getByRole('combobox', { name: 'Show on map or globe' }),
    'reported',
  );
  await openMapTool(user, 'On this map');
  await user.click(screen.getByRole('button', { name: 'Download live GeoJSON' }));
  const selected = JSON.parse(await readBlob(downloads[0]!)) as { features: { id: string }[] };
  expect(selected.features.map((row) => row.id)).toEqual(['reported']);
  // The excluded event stays in the local mirror; the exporter must use the map's selection.
  expect(useEventsStore.getState().list).toHaveLength(2);

  await openMapTool(user, 'Location quality');
  await user.selectOptions(
    screen.getByRole('combobox', { name: 'Show on map or globe' }),
    'approximate',
  );
  await openMapTool(user, 'On this map');
  await user.click(screen.getByRole('button', { name: 'Download live KML' }));
  const xml = new DOMParser().parseFromString(await readBlob(downloads[1]!), 'application/xml');
  expect(xml.querySelector('parsererror')).toBeNull();
  expect([...xml.querySelectorAll('Placemark > name')].map((row) => row.textContent)).toEqual([
    'Approximate earthquake',
  ]);
});
