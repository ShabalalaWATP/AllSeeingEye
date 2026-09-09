import { act, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { server } from '@/test/server';
import { infrastructureSchema, type Infrastructure } from '@/lib/api/infrastructure';
import { useInfrastructure } from './useInfrastructure';
import { buildInfrastructureLayers } from './infrastructureLayers';
import { InfrastructurePanel } from './InfrastructurePanel';
import { InfrastructureInspector } from './InfrastructureInspector';

const data: Infrastructure = {
  cables: [
    {
      id: 'c1',
      name: 'Atlantic segment',
      category: 'telecom',
      path: [
        [-10, 40],
        [-12, 42],
      ],
      source_url: 'https://www.openstreetmap.org/way/1',
      note: 'Approximate public route.',
    },
  ],
  ground_stations: [
    {
      id: 'g1',
      name: 'Esrange',
      operator: 'SSC Space',
      country: 'SE',
      longitude: 21.07,
      latitude: 67.88,
      source_url: 'https://sscspace.com/',
      note: 'Approximate public location.',
    },
  ],
  snapshot_date: '2026-09-08',
  cable_attribution: 'OpenStreetMap contributors',
  cable_licence_url: 'https://opendatacommons.org/licenses/odbl/',
  nuclear_facilities: [],
  nuclear_attribution: 'WRI historical inventory',
  nuclear_licence_url: 'https://creativecommons.org/licenses/by/4.0/',
  nuclear_dataset_version: '1.3.0',
  nuclear_snapshot_date: '2026-09-09',
};
const cableFixture = data.cables[0]!;
const stationFixture = data.ground_stations[0]!;

it('rejects unsafe links, out-of-range positions and oversized route data', () => {
  expect(infrastructureSchema.safeParse(data).success).toBe(true);
  for (const source_url of [
    'javascript:alert(1)',
    'https://user:password@example.org/',
    'http://example.org/',
    'https://example.org:123/',
  ])
    expect(
      infrastructureSchema.safeParse({ ...data, cables: [{ ...data.cables[0], source_url }] })
        .success,
    ).toBe(false);
  expect(
    infrastructureSchema.safeParse({
      ...data,
      ground_stations: [{ ...data.ground_stations[0], latitude: 91 }],
    }).success,
  ).toBe(false);
  expect(
    infrastructureSchema.safeParse({
      ...data,
      cables: [{ ...data.cables[0], path: Array.from({ length: 513 }, () => [0, 0]) }],
    }).success,
  ).toBe(false);
});

it('loads lazily, retries failures, and clears selection when closing or disabling a layer', async () => {
  let calls = 0;
  server.use(
    http.get('/api/map-infrastructure', () => {
      calls++;
      return calls === 1 ? new HttpResponse(null, { status: 503 }) : HttpResponse.json(data);
    }),
  );
  const { result } = renderHook(() => useInfrastructure());
  expect(calls).toBe(0);
  act(() => result.current.toggleCables());
  await waitFor(() => expect(result.current.error).toContain('could not be loaded'));
  act(() => result.current.retry());
  await waitFor(() => expect(result.current.data).toEqual(data));
  expect(result.current.loading).toBe(false);
  act(() => result.current.select({ kind: 'cable', item: cableFixture }));
  expect(result.current.selected?.kind).toBe('cable');
  act(() => result.current.close());
  expect(result.current.selected).toBeNull();
  act(() => result.current.select({ kind: 'cable', item: cableFixture }));
  act(() => result.current.toggleCables());
  expect(result.current.selected).toBeNull();
  act(() => result.current.toggleStations());
  await waitFor(() => expect(calls).toBe(3));
  act(() => result.current.select({ kind: 'station', item: stationFixture }));
  expect(result.current.selected?.kind).toBe('station');
  act(() => result.current.toggleStations());
  expect(result.current.selected).toBeNull();
});

it('builds pickable cable and dish layers in both modes and removes highlights after close', () => {
  const onSelect = vi.fn();
  expect(
    buildInfrastructureLayers(
      { data: null, cablesEnabled: true, stationsEnabled: true, selected: null },
      onSelect,
    ),
  ).toEqual([]);
  for (const globe of [false, true]) {
    const base = { data, cablesEnabled: true, stationsEnabled: true, selected: null };
    const layers = buildInfrastructureLayers(base, onSelect, globe);
    expect(layers.map((layer) => layer.id)).toEqual([
      'undersea-cables',
      'satellite-ground-stations',
    ]);
    const cable = layers[0]!;
    const station = layers[1]!;
    expect(cable.props.pickable).toBe(true);
    expect(station.props.pickable).toBe(true);
    // Deck callbacks are invoked directly without requiring a GPU in unit tests.
    const clickCable = cable.props.onClick as (info: unknown) => boolean;
    const clickStation = station.props.onClick as (info: unknown) => boolean;
    clickCable({ object: data.cables[0] });
    clickStation({ object: data.ground_stations[0] });
    clickCable({});
    clickStation({});
    expect(onSelect).toHaveBeenCalledWith({ kind: 'cable', item: cableFixture });
    expect(onSelect).toHaveBeenCalledWith({ kind: 'station', item: stationFixture });
    const selected = buildInfrastructureLayers(
      { ...base, selected: { kind: 'station', item: stationFixture } },
      onSelect,
      globe,
    );
    expect(selected.at(-1)?.id).toBe('selected-ground-station-halo');
    expect(
      buildInfrastructureLayers(
        { ...base, cablesEnabled: false, stationsEnabled: false },
        onSelect,
        globe,
      ),
    ).toEqual([]);
    expect(layers.some((layer) => layer.id.includes('halo'))).toBe(false);
  }
});

it('supports panel searching, source attribution and an accessible inspector close', async () => {
  server.use(http.get('/api/map-infrastructure', () => HttpResponse.json(data)));
  function Panel() {
    const state = useInfrastructure();
    return (
      <>
        <InfrastructurePanel state={state} onSelect={state.select} />
        {state.selected && (
          <InfrastructureInspector selected={state.selected} onClose={state.close} />
        )}
      </>
    );
  }
  const user = userEvent.setup();
  render(<Panel />);
  await user.click(screen.getByRole('switch', { name: 'Satellite ground stations' }));
  await screen.findByText(/Snapshot: 2026/);
  expect(screen.getByRole('link', { name: 'Cable data licence' })).toHaveAttribute(
    'href',
    data.cable_licence_url,
  );
  await user.type(screen.getByRole('searchbox'), 'missing');
  expect(screen.getByText(/No matching infrastructure/)).toBeInTheDocument();
  await user.clear(screen.getByRole('searchbox'));
  await user.click(screen.getByRole('button', { name: /Esrange/ }));
  expect(screen.getByRole('button', { name: 'Close infrastructure details' })).toHaveFocus();
  expect(screen.getByText('Approximate location')).toBeInTheDocument();
  fireEvent.keyDown(window, { key: 'Escape' });
  expect(
    screen.queryByRole('complementary', { name: 'Infrastructure details' }),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole('switch', { name: 'Undersea cables' }));
  await user.click(screen.getByRole('button', { name: /Atlantic segment/ }));
  expect(screen.getByText('Approximate route')).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Close infrastructure details' }));
  expect(
    screen.queryByRole('complementary', { name: 'Infrastructure details' }),
  ).not.toBeInTheDocument();
});
