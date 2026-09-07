import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it, vi } from 'vitest';
import { applySession } from '@/test/render';
import { server } from '@/test/server';
import { mockWebGl2 } from '@/test/env';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import { savedMapFixture, mapEvidence } from '@/test/fixtures.savedMaps';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { mapStateSchema } from '@/lib/api/mapViews';
import type { MapState, SavedMapView } from '@/lib/api/mapViews';
import ReportEvidenceMap from './ReportEvidenceMap';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/mapbox', () => import('@/test/fakeDeck'));
const measurement = {
  mode: 'distance' as const,
  method: 'wgs84-geographiclib-2.2.0-v1' as const,
  points: [
    [179, 0],
    [-179, 0],
  ] as [number, number][],
};
function mount(savedView: SavedMapView = savedMapFixture) {
  return render(
    <ReportEvidenceMap
      reportId={savedView.view.report_id}
      version={1}
      evidence={mapEvidence}
      savedView={savedView}
      canManageView={() => true}
    />,
  );
}
beforeEach(() => {
  applySession('user');
  mockWebGl2(true);
  FakeMap.reset();
  MapboxOverlay.reset();
});

it('saves original typed coordinates without derived totals and reopens the same measurement without WebGL', async () => {
  mockWebGl2(false);
  let submitted: MapState | undefined;
  let revision: SavedMapView | undefined;
  server.use(
    http.patch('/api/map/views/:id', async ({ request }) => {
      const body = (await request.json()) as { state: MapState };
      submitted = body.state;
      revision = {
        ...savedMapFixture,
        revision: { ...savedMapFixture.revision, number: 2, state: body.state },
      };
      return HttpResponse.json(revision);
    }),
  );
  const view = mount();
  const user = userEvent.setup();
  expect(screen.getByRole('button', { name: 'Pick points on map' })).toBeDisabled();
  for (const [lon, lat] of measurement.points) {
    fireEvent.change(screen.getByLabelText('Longitude'), { target: { value: lon } });
    fireEvent.change(screen.getByLabelText('Latitude'), { target: { value: lat } });
    await user.click(screen.getByRole('button', { name: 'Add coordinate' }));
  }
  const result = screen.getByLabelText('Measurement result').textContent;
  expect(result).toContain('222.639 km');
  await user.click(screen.getByRole('button', { name: 'Save new revision' }));
  await screen.findByText('Saved immutable revision 2.');
  expect(submitted?.measurement).toEqual(measurement);
  expect(submitted?.aoi).toEqual(savedMapFixture.revision.state.aoi);
  view.unmount();
  expect(revision).toBeDefined();
  mount(revision);
  expect(screen.getByLabelText('Measurement result')).toHaveTextContent(result);
  expect(FakeMap.instances).toHaveLength(0);
  await user.click(screen.getByRole('button', { name: 'Clear measure' }));
  expect(screen.getByLabelText('Longitude')).toHaveValue(null);
  expect(screen.getByText('0/32 points')).toBeVisible();
});

it('picks only in explicit measurement mode, keeps coordinates across projections and clears private layers on revocation', async () => {
  mount({
    ...savedMapFixture,
    revision: {
      ...savedMapFixture.revision,
      state: { ...savedMapFixture.revision.state, measurement },
    },
  });
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Open evidence map' }));
  await act(async () => {
    await vi.dynamicImportSettled();
  });
  await screen.findByRole('region', { name: 'Saved evidence flat map' });
  const map = FakeMap.instances[0]!;
  act(() => map.fire('style.load'));
  const click = (lon: number, lat: number) =>
    act(() => map.fire('click', { lngLat: { lng: lon, lat } }));
  click(0, 0);
  expect(screen.getByText('2/32 points')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Pick points on map' }));
  click(0, 0);
  expect(screen.getByText('3/32 points')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Globe' }));
  const layers = MapboxOverlay.instances[0]!.props.layers as {
    id: string;
    props: { data: unknown[] };
  }[];
  expect(layers.find((layer) => layer.id === 'measurement-points')?.props.data).toEqual([
    ...measurement.points,
    [0, 0],
  ]);
  expect(FakeMap.instances).toHaveLength(1);
  await user.click(screen.getByText('Select a map area'));
  await user.click(screen.getByRole('button', { name: 'Choose two map corners' }));
  expect(screen.getByRole('button', { name: 'Pick points on map' })).toBeDisabled();
  click(10, 20);
  expect(screen.getByText('3/32 points')).toBeVisible();
  act(() => invalidateWorkspaceAccess());
  expect(screen.queryByLabelText('Measurement result')).not.toBeInTheDocument();
  expect(map.remove).toHaveBeenCalled();
  expect(MapboxOverlay.instances[0]!.props.layers).toEqual([]);
});

it('validates the method and bounded exact coordinates while accepting legacy views', () => {
  const legacy = { ...savedMapFixture.revision.state };
  delete (legacy as Partial<MapState>).measurement;
  expect(mapStateSchema.parse(legacy).measurement).toBeNull();
  for (const invalid of [
    { ...measurement, method: 'unknown' },
    { ...measurement, points: Array.from({ length: 33 }, () => [0, 0]) },
    { ...measurement, points: [[181, 0]] },
    { ...measurement, points: [[0, NaN]] },
    { ...measurement, points: [['1', 0]] },
    { ...measurement, points: [[0, 0, 0]] },
    { ...measurement, metres: 1 },
  ])
    expect(mapStateSchema.safeParse({ ...legacy, measurement: invalid }).success).toBe(false);
});
