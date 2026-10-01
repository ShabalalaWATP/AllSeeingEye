import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useState } from 'react';
import { MemoryRouter, useLocation } from 'react-router';
import { beforeEach, expect, it, vi } from 'vitest';

import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';
import { plainUser } from '@/test/fixtures';
import { server } from '@/test/server';
import { LiveViewNotice } from './LiveViewNotice';
import { LiveViewsPanel } from './LiveViewsPanel';
import type { FlightFilter } from './flightFilters';
import { useLiveViewControls, type LiveViewSources } from './useLiveViewControls';
import { useLiveViewLibrary } from './useLiveViewLibrary';
import { useLiveViewOpening } from './useLiveViewOpening';

const VIEW_ID = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const camera = { center: [24.5, 57.2] as [number, number], zoom: 4.5, bearing: 0, pitch: 0 };
const restoreCamera = vi.fn();
const engine = { getCamera: () => camera, restoreCamera };
let stored: Record<string, unknown> | null = null;

function documentFor(payload: Record<string, unknown>, title = 'Baltic') {
  return {
    id: VIEW_ID,
    kind: 'live_view',
    title,
    payload,
    revision: 1,
    created_by: plainUser.id,
    team_id: null,
    created_at: '2026-09-30T00:00:00Z',
    updated_at: '2026-09-30T00:00:00Z',
  };
}

function Harness() {
  const globe = useGlobeStore();
  const events = useEventsStore();
  const [visibility, setVisibility] = useState({ aircraft: true, vessels: true, firms: true });
  const [flightFilter, setFlightFilter] = useState<FlightFilter>('all');
  const [vesselFilter, setVesselFilter] = useState<FlightFilter>('all');
  const [fires, setFires] = useState(false);
  const [quality, setQuality] = useState<LiveViewSources['quality']['filter']>('all');
  const [level, setLevel] = useState<'all' | 'red'>('all');
  const [minimum, setMinimum] = useState(5);
  const [group, setGroup] = useState<LiveViewSources['conflicts']['group']>('all');
  const [historical, setHistorical] = useState(false);
  const [unreviewed, setUnreviewed] = useState(false);
  const [precision, setPrecision] = useState<LiveViewSources['conflicts']['precision']>('all');
  const controls = useLiveViewControls({
    engine,
    mode: globe.mode,
    setMode: globe.setMode,
    baseLayer: globe.baseLayer,
    setBaseLayer: globe.setBaseLayer,
    terminator: globe.terminator,
    toggleTerminator: globe.toggleTerminator,
    interference: globe.interference,
    toggleInterference: globe.toggleInterference,
    hidden: events.hidden,
    toggleCategory: events.toggleCategory,
    windowHours: events.windowHours,
    setWindow: events.setWindow,
    country: events.country,
    setCountry: events.setCountry,
    observations: {
      visibility,
      toggle: (kind) => setVisibility((previous) => ({ ...previous, [kind]: !previous[kind] })),
      flightFilter,
      setFlightFilter,
      vesselFilter,
      setVesselFilter,
    },
    fires: { enabled: fires, toggleEnabled: () => setFires((value) => !value) },
    quality: { filter: quality, setFilter: setQuality },
    gnss: { level, setLevel, minimum, setMinimum },
    conflicts: {
      group,
      setGroup,
      includeHistorical: historical,
      setIncludeHistorical: setHistorical,
      includeUnreviewed: unreviewed,
      setIncludeUnreviewed: setUnreviewed,
      precision,
      setPrecision,
    },
  });
  const opening = useLiveViewOpening(controls);
  const library = useLiveViewLibrary();
  const location = useLocation();
  return (
    <>
      <output data-testid="flight">{flightFilter}</output>
      <output data-testid="aircraft">{String(visibility.aircraft)}</output>
      <output data-testid="minimum">{minimum}</output>
      <output data-testid="search">{location.search}</output>
      <button type="button" onClick={() => setFlightFilter('military')}>
        Military only
      </button>
      <button type="button" onClick={() => setMinimum(25)}>
        At least 25
      </button>
      <LiveViewNotice notice={opening.notice} onClose={opening.dismiss} />
      <LiveViewsPanel library={library} controls={controls} onOpen={opening.openId} />
    </>
  );
}

function renderAt(path = '/') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Harness />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  stored = null;
  restoreCamera.mockReset();
  useAuthStore.setState({ user: plainUser, status: 'authenticated' });
  useGlobeStore.setState({ mode: 'globe', interference: false, terminator: false });
  useEventsStore.setState({ hidden: ['news', 'aviation'], windowHours: null, country: null });
  server.use(
    http.get('/api/map/workspaces', () => HttpResponse.json(stored ? [documentFor(stored)] : [])),
    http.post('/api/map/workspaces', async ({ request }) => {
      const body = (await request.json()) as { kind: string; payload: Record<string, unknown> };
      expect(body.kind).toBe('live_view');
      stored = body.payload;
      return HttpResponse.json(documentFor(stored), { status: 201 });
    }),
    http.get('/api/map/workspaces/:id', () =>
      stored
        ? HttpResponse.json(documentFor(stored))
        : HttpResponse.json({ detail: 'Not found.' }, { status: 404 }),
    ),
  );
});

it('saves the current view configuration and restores it when explicitly opened', async () => {
  renderAt();
  await screen.findByText('No saved views yet.');
  act(() => {
    useEventsStore.getState().toggleCategory('aviation');
    useEventsStore.getState().setWindow(24);
    useEventsStore.getState().setCountry('EE');
    useGlobeStore.getState().setMode('map');
    useGlobeStore.getState().toggleInterference();
  });
  fireEvent.click(screen.getByRole('button', { name: 'Military only' }));
  fireEvent.click(screen.getByRole('button', { name: 'At least 25' }));
  fireEvent.change(screen.getByLabelText('View name'), { target: { value: 'Baltic' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save as new view' }));
  await screen.findByText('Saved Baltic (revision 1).');
  expect(stored).toMatchObject({
    projection: 'map',
    window_hours: 24,
    nation: 'EE',
    camera,
    filters: { flight: 'military', gnss_minimum: 25 },
  });
  expect(stored?.layers).toEqual(expect.arrayContaining(['aviation', 'aircraft', 'interference']));
  expect(stored?.layers).not.toContain('news');
  expect(Object.keys(stored ?? {})).not.toContain('events');

  act(() => {
    useEventsStore.setState({ hidden: ['news', 'aviation'], windowHours: null, country: null });
    useGlobeStore.setState({ mode: 'globe', interference: false });
  });
  expect(useGlobeStore.getState().mode).toBe('globe');
  fireEvent.click(screen.getByRole('button', { name: 'Open Baltic' }));
  await screen.findByText('Baltic');
  await waitFor(() => expect(restoreCamera).toHaveBeenCalledWith(camera));
  expect(useGlobeStore.getState()).toMatchObject({ mode: 'map', interference: true });
  expect(useEventsStore.getState()).toMatchObject({ windowHours: 24, country: 'EE' });
  expect(useEventsStore.getState().hidden).toEqual(['news']);
  expect(screen.getByTestId('flight')).toHaveTextContent('military');
  expect(screen.getByTestId('minimum')).toHaveTextContent('25');
});

it('opens a link by ID, drops retired layers with a notice and removes the ID', async () => {
  stored = {
    version: 1,
    projection: 'globe',
    camera,
    base_layer: 'dark',
    layers: ['conflict', 'retired_layer'],
    window_hours: 6,
    nation: null,
    filters: { flight: 'military', legacy: true },
    plan_id: null,
  };
  renderAt(`/?view=${VIEW_ID}`);
  await screen.findByText(/No longer available, so left out: layer retired_layer, filter legacy/);
  expect(screen.getByTestId('search')).toHaveTextContent('');
  expect(useEventsStore.getState().windowHours).toBe(6);
  expect(useEventsStore.getState().hidden).not.toContain('conflict');
  expect(screen.getByTestId('aircraft')).toHaveTextContent('false');
});

it('shows a stale or inaccessible link as unavailable and changes nothing', async () => {
  renderAt(`/?view=${VIEW_ID}`);
  expect(
    await screen.findByText('This saved view is unavailable or you no longer have access.'),
  ).toBeInTheDocument();
  expect(useGlobeStore.getState().mode).toBe('globe');
  expect(useEventsStore.getState().windowHours).toBeNull();
  expect(restoreCamera).not.toHaveBeenCalled();
});

it('never opens a view on its own and clears its notice when access changes', async () => {
  let reads = 0;
  server.use(
    http.get('/api/map/workspaces/:id', () => {
      reads += 1;
      return HttpResponse.json({ detail: 'Not found.' }, { status: 404 });
    }),
  );
  stored = null;
  const first = renderAt();
  await screen.findByText('No saved views yet.');
  expect(reads).toBe(0);
  first.unmount();
  renderAt(`/?view=${VIEW_ID}`);
  await screen.findByRole('alert');
  act(() => invalidateWorkspaceAccess());
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});
