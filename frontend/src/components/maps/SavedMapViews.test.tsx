import { act, render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it, vi } from 'vitest';
import { applySession } from '@/test/render';
import { server } from '@/test/server';
import { mockWebGl2 } from '@/test/env';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import type { MapState } from '@/lib/api/mapViews';
import ReportEvidenceMap from './ReportEvidenceMap';
import { mapEvidence, savedMapFixture as saved } from '@/test/fixtures.savedMaps';
import { initialMapState, matchesMapFilters } from './savedMapState';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/mapbox', () => import('@/test/fakeDeck'));
vi.mock('./FootprintSearchPanel', () => ({
  FootprintSearchPanel: ({ onChange }: { onChange: (value: unknown) => void }) => (
    <button
      onClick={() =>
        onChange({
          type: 'FeatureCollection',
          features: [
            {
              type: 'Feature',
              id: 0,
              properties: { label: 'Footprint' },
              geometry: { type: 'Point', coordinates: [0, 0] },
            },
          ],
        })
      }
    >
      Show temporary footprints
    </button>
  ),
}));
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
      savedView={saved}
      canCreateView
      canManageView={() => true}
      scopeLabel="Personal"
    />,
  );
}
async function open() {
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Open evidence map' }));
  await act(async () => {
    await vi.dynamicImportSettled();
  });
  await screen.findByRole('region', { name: 'Saved evidence flat map' });
  return user;
}

it('roundtrips all saved state and captures a manually moved camera without replaying selection', async () => {
  let submitted: MapState | undefined;
  server.use(
    http.patch('/api/map/views/:id', async ({ request }) => {
      const body = (await request.json()) as { state: MapState; base_revision_id: string };
      expect(body.base_revision_id).toBe(saved.revision.id);
      submitted = body.state;
      return HttpResponse.json({
        ...saved,
        view: { ...saved.view, latest_revision_id: 'revision-2' },
        revision: { ...saved.revision, id: 'revision-2', number: 2, state: body.state },
      });
    }),
  );
  mount();
  expect(FakeMap.instances).toHaveLength(0);
  const user = await open();
  const map = FakeMap.instances[0]!;
  expect(map.jumpTo).toHaveBeenCalledWith({ center: [40, 35], zoom: 6, bearing: 25, pitch: 20 });
  expect(map.flyTo).not.toHaveBeenCalled();
  expect(map.options.style).toContain('positron');
  vi.spyOn(map, 'getCenter').mockReturnValue({ lng: 55, lat: 45 });
  vi.spyOn(map, 'getZoom').mockReturnValue(8);
  map.getBearing.mockReturnValue(10);
  map.getPitch.mockReturnValue(30);
  act(() => map.fire('moveend'));
  await user.click(screen.getByRole('button', { name: 'Save new revision' }));
  await screen.findByText('Saved immutable revision 2.');
  expect(submitted).toEqual({
    ...saved.revision.state,
    camera: { longitude: 55, latitude: 45, zoom: 8, bearing: 10, pitch: 30 },
  });
  expect(screen.getByRole('link', { name: /Open saved revision 2/ })).toHaveAttribute(
    'href',
    expect.stringContaining('version=1&map_view=view-1&map_revision=revision-2'),
  );
  await user.click(screen.getByRole('button', { name: /E1: Located record/ }));
  expect(map.jumpTo).toHaveBeenCalledWith({ center: [10, 50], zoom: 4 });
  act(() => map.fire('moveend'));
  await user.click(screen.getByRole('button', { name: 'Close evidence map' }));
  await open();
  expect(FakeMap.instances[1]!.jumpTo).toHaveBeenCalledTimes(1);
  expect(FakeMap.instances[1]!.jumpTo).toHaveBeenCalledWith({
    center: [55, 45],
    zoom: 8,
    bearing: 10,
    pitch: 30,
  });
});

it('retains edits on conflict and blocks saving visible temporary footprints', async () => {
  server.use(
    http.patch('/api/map/views/:id', () =>
      HttpResponse.json(
        { error: { code: 'conflict', message: 'A newer revision exists.' } },
        { status: 409 },
      ),
    ),
  );
  mount();
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Save new revision' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('A newer revision exists');
  expect(screen.getByLabelText('Map view title')).toHaveValue('Saved geography');
  await user.click(screen.getByRole('button', { name: 'Show temporary footprints' }));
  expect(screen.getByRole('button', { name: 'Save new revision' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Save separate copy' })).toBeDisabled();
  expect(screen.getByText(/Clear the temporary catalogue footprints/)).toBeVisible();
});

it('invalidates rendered private geometry after the server denies a mutation', async () => {
  server.use(
    http.patch('/api/map/views/:id', () =>
      HttpResponse.json({ error: { code: 'not_found', message: 'Not found.' } }, { status: 404 }),
    ),
  );
  mount();
  const user = await open();
  await user.click(screen.getByRole('button', { name: 'Save new revision' }));
  await screen.findByText(/Account or access changed/);
  expect(screen.queryByRole('region', { name: 'Saved evidence flat map' })).not.toBeInTheDocument();
  expect(MapboxOverlay.instances[0]!.props.layers).toEqual([]);
});

it('browses exact revision links, archives without losing the existing link, and creates a copy', async () => {
  let copied = false;
  server.use(
    http.get('/api/map/views', () =>
      HttpResponse.json({
        items: [
          {
            view: saved.view,
            title: saved.revision.title,
            revision_number: 1,
            report_version_number: 1,
            updated_at: saved.revision.created_at,
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      }),
    ),
    http.delete('/api/map/views/:id', () => new HttpResponse(null, { status: 204 })),
    http.post('/api/map/views', () => {
      copied = true;
      return HttpResponse.json(saved);
    }),
  );
  mount();
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Browse saved views' }));
  expect(
    await screen.findByRole('link', { name: /Saved geography, revision 1, report version 1/ }),
  ).toHaveAttribute('href', expect.stringContaining('map_revision=revision-1'));
  await user.click(screen.getByRole('button', { name: 'Archive view' }));
  await screen.findByText(/View archived/);
  expect(screen.queryByRole('button', { name: 'Save new revision' })).not.toBeInTheDocument();
  expect(screen.getByRole('link', { name: /Open saved revision 1/ })).toHaveTextContent('archived');
  await user.click(screen.getByRole('button', { name: 'Save separate copy' }));
  await waitFor(() => expect(copied).toBe(true));
});

it('honours unknown-date exclusion without bounds and clears both bounds for All publication dates', async () => {
  expect(
    matchesMapFilters(
      { ...mapEvidence[0]!, published_at: '' },
      { ...initialMapState(), include_unknown_dates: false },
    ),
  ).toBe(false);
  mount();
  const user = userEvent.setup();
  await user.selectOptions(screen.getByLabelText('Publication timeline (UTC)'), '');
  expect(screen.getByLabelText('Published from (UTC)')).toHaveValue('');
  expect(screen.getByLabelText('Published until (UTC)')).toHaveValue('');
  expect(screen.getByLabelText('Include unknown publication dates')).toBeChecked();
});

it('aborts a pending save before a delayed401 can retry under another account', async () => {
  let started = false,
    aborted = false,
    refreshes = 0;
  let finish: () => void = () => undefined;
  const done = new Promise<void>((resolve) => {
    finish = resolve;
  });
  server.use(
    http.patch('/api/map/views/:id', async ({ request }) => {
      started = true;
      request.signal.addEventListener('abort', () => {
        aborted = true;
      });
      await done;
      return HttpResponse.json(
        { error: { code: 'unauthenticated', message: 'Expired' } },
        { status: 401 },
      );
    }),
    http.post('/api/auth/refresh', () => {
      refreshes++;
      return new HttpResponse(null, { status: 401 });
    }),
  );
  const view = mount();
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Save new revision' }));
  await waitFor(() => expect(started).toBe(true));
  act(() => applySession('admin'));
  await waitFor(() => expect(aborted).toBe(true));
  finish();
  expect(refreshes).toBe(0);
  expect(screen.queryByLabelText('Map view title')).not.toBeInTheDocument();
  view.unmount();
});

it('shows a lower-bound-only range as custom so All publication dates can clear it', async () => {
  const lowerOnly = {
    ...saved,
    revision: { ...saved.revision, state: { ...saved.revision.state, published_until: null } },
  };
  render(
    <ReportEvidenceMap
      reportId={saved.view.report_id}
      version={1}
      evidence={mapEvidence}
      savedView={lowerOnly}
    />,
  );
  expect(screen.getByLabelText('Publication timeline (UTC)')).toHaveValue('__since_only__');
  const user = userEvent.setup();
  await user.selectOptions(screen.getByLabelText('Publication timeline (UTC)'), '');
  expect(screen.getByLabelText('Published from (UTC)')).toHaveValue('');
  expect(screen.getByLabelText('Publication timeline (UTC)')).toHaveValue('');
});
