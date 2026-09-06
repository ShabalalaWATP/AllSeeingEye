import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { applySession } from '@/test/render';
import { mockWebGl2 } from '@/test/env';
import { server } from '@/test/server';
import { savedMapFixture as saved, mapEvidence } from '@/test/fixtures.savedMaps';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import type { MapState } from '@/lib/api/mapViews';
import { rectangleArea } from '@/lib/map/areaGeometry';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import ReportEvidenceMap from './ReportEvidenceMap';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/mapbox', () => import('@/test/fakeDeck'));
beforeEach(() => {
  applySession('user');
  mockWebGl2(true);
  FakeMap.reset();
  MapboxOverlay.reset();
});
function mount() {
  return render(
    <ReportEvidenceMap
      reportId={saved.view.report_id}
      version={1}
      evidence={mapEvidence}
      canCreateView
      canManageView={() => true}
    />,
  );
}
async function open() {
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Open evidence map' }));
  await act(async () => {
    await vi.dynamicImportSettled();
  });
  await screen.findByRole('region', { name: 'Saved evidence globe' });
  return user;
}
function enter(bounds: { west: number; east: number; south: number; north: number }) {
  for (const [field, value] of Object.entries(bounds))
    fireEvent.change(screen.getByLabelText(`Area ${field}`), { target: { value: String(value) } });
}

it('applies a keyboard rectangle locally, preserves it across projections and saves only explicitly', async () => {
  let requests = 0;
  let posted: MapState | undefined;
  server.use(
    http.post('/api/map/views', async ({ request }) => {
      requests++;
      const body = (await request.json()) as { state: MapState };
      posted = body.state;
      return HttpResponse.json({ ...saved, revision: { ...saved.revision, state: body.state } });
    }),
  );
  mount();
  const user = await open();
  await user.click(screen.getByText('Select a map area'));
  const bounds = { west: 170, east: -170, south: 10, north: 20 };
  enter(bounds);
  expect(screen.getByRole('button', { name: 'Save map view' })).toBeDisabled();
  await user.click(screen.getByRole('button', { name: 'Apply rectangle' }));
  expect(requests).toBe(0);
  const layer = () =>
    (MapboxOverlay.instances[0]!.props.layers as { id: string; props: { data: unknown } }[]).find(
      (item) => item.id === 'saved-research-area',
    );
  expect(layer()?.props.data).toEqual(rectangleArea(bounds));
  await user.click(screen.getByRole('button', { name: 'Flat map' }));
  expect(layer()?.props.data).toEqual(rectangleArea(bounds));
  expect(FakeMap.instances).toHaveLength(1);
  await user.click(screen.getByRole('button', { name: 'Save map view' }));
  await screen.findByText('Saved immutable revision 1.');
  expect(posted?.aoi).toEqual(rectangleArea(bounds));
  await user.click(screen.getByRole('button', { name: 'Clear selected area' }));
  expect(layer()).toBeUndefined();
  expect(requests).toBe(1);
});

it('captures the viewport envelope as an unapplied draft with explicit bounds and handles unavailable maps', async () => {
  mount();
  const user = await open();
  await user.click(screen.getByText('Select a map area'));
  FakeMap.instances[0]!.getBounds.mockReturnValue({
    getWest: () => 170,
    getEast: () => 190,
    getSouth: () => -5,
    getNorth: () => 5,
  });
  await user.click(screen.getByRole('button', { name: 'Use viewport envelope' }));
  expect(screen.getByLabelText('Area west')).toHaveValue(170);
  expect(screen.getByLabelText('Area east')).toHaveValue(-170);
  expect(
    screen.getByText(/Viewport bounding envelope, not an exact visible-ground polygon/),
  ).toBeVisible();
  expect(screen.getByRole('button', { name: 'Save map view' })).toBeDisabled();
  await user.click(screen.getByRole('button', { name: 'Discard area draft' }));
  expect(screen.getByRole('button', { name: 'Save map view' })).toBeEnabled();
  await user.click(screen.getByRole('button', { name: 'Close evidence map' }));
  expect(screen.getByRole('button', { name: 'Use viewport envelope' })).toBeDisabled();
});

it('reviews two map corners before applying and clears private area draft on access change', async () => {
  mount();
  const user = await open();
  await user.click(screen.getByText('Select a map area'));
  await user.click(screen.getByRole('button', { name: 'Choose two map corners' }));
  act(() => FakeMap.instances[0]!.fire('click', { lngLat: { lng: 170, lat: 10 } }));
  expect(screen.getByText(/First corner: 170, 10/)).toBeVisible();
  act(() => FakeMap.instances[0]!.fire('click', { lngLat: { lng: -170, lat: 20 } }));
  expect(screen.getByLabelText('Area west')).toHaveValue(170);
  expect(screen.getByLabelText('Area east')).toHaveValue(-170);
  expect(screen.getByText(/Two corners use the shorter longitude span/)).toBeVisible();
  expect(screen.getByRole('button', { name: 'Save map view' })).toBeDisabled();
  await user.click(screen.getByRole('button', { name: 'Apply rectangle' }));
  act(() => invalidateWorkspaceAccess());
  await screen.findByText(/Account or access changed/);
  expect(screen.queryByLabelText('Area west')).not.toBeInTheDocument();
  expect(MapboxOverlay.instances[0]!.props.layers).toEqual([]);
});

it('does not replace an existing arbitrary polygon merely by opening or editing the controls', async () => {
  const aoi = {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        id: 0,
        properties: { label: 'Original triangle' },
        geometry: {
          type: 'Polygon',
          coordinates: [
            [
              [0, 0],
              [4, 0],
              [1, 3],
              [0, 0],
            ],
          ],
        },
      },
    ],
  };
  const original = {
    ...saved,
    revision: { ...saved.revision, state: { ...saved.revision.state, aoi } },
  };
  let posted: MapState | undefined;
  server.use(
    http.patch('/api/map/views/:id', async ({ request }) => {
      const body = (await request.json()) as { state: MapState };
      posted = body.state;
      return HttpResponse.json({
        ...original,
        revision: { ...original.revision, state: body.state },
      });
    }),
  );
  render(
    <ReportEvidenceMap
      reportId={saved.view.report_id}
      version={1}
      evidence={mapEvidence}
      savedView={original}
      canCreateView
      canManageView={() => true}
    />,
  );
  const user = userEvent.setup();
  await user.click(screen.getByText('Select a map area'));
  enter({ west: 0, east: 1, south: 2, north: 1 });
  await user.click(screen.getByRole('button', { name: 'Apply rectangle' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('north greater than south');
  await user.click(screen.getByRole('button', { name: 'Discard area draft' }));
  await user.click(screen.getByRole('button', { name: 'Save new revision' }));
  await waitFor(() => expect(posted?.aoi).toEqual(aoi));
});

it('does not invent viewport bounds when WebGL is unavailable', async () => {
  mockWebGl2(false);
  mount();
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Open evidence map' }));
  await screen.findByText(/WebGL2 is unavailable/);
  await user.click(screen.getByText('Select a map area'));
  await user.click(screen.getByRole('button', { name: 'Use viewport envelope' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Open a supported map');
  expect(screen.getByLabelText('Area west')).toHaveValue(null);
  expect(FakeMap.instances).toHaveLength(0);
});
