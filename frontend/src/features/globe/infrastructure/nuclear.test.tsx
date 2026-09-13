import { act, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { server } from '@/test/server';
import { infrastructureSchema, type Infrastructure } from '@/lib/api/infrastructure';
import { useInfrastructure } from './useInfrastructure';
import { InfrastructurePanel } from './InfrastructurePanel';
import { InfrastructureInspector } from './InfrastructureInspector';
import { buildInfrastructureLayers } from './infrastructureLayers';

const plant = {
  id: 'n1',
  name: 'Historical plant',
  country: 'United Kingdom',
  country_code: 'GBR',
  longitude: -2,
  latitude: 54,
  capacity_mw: 1200,
  capacity_year: 2017,
  operator: null,
  source_name: 'WRI GPPD',
  source_url: 'https://datasets.wri.org/',
  geolocation_source: 'Public inventory',
  note: 'Historical location, not current operating status.',
};
const data: Infrastructure = {
  data_centres: [],
  data_centre_attribution: 'OpenStreetMap contributors',
  data_centre_licence_url: 'https://www.openstreetmap.org/copyright',
  data_centre_snapshot_date: '2026-09-13',
  cables: [],
  ground_stations: [],
  snapshot_date: '2026-09-09',
  cable_attribution: 'OSM',
  cable_licence_url: 'https://opendatacommons.org/licenses/odbl/',
  nuclear_facilities: [plant],
  nuclear_attribution: 'World Resources Institute',
  nuclear_licence_url: 'https://creativecommons.org/licenses/by/4.0/',
  nuclear_dataset_version: '1.3.0',
  nuclear_snapshot_date: '2026-09-09',
};

it('loads nuclear independently, selects and clears its highlight with details or toggle', async () => {
  server.use(http.get('/api/map-infrastructure', () => HttpResponse.json(data)));
  const { result } = renderHook(() => useInfrastructure());
  expect(result.current.nuclearEnabled).toBe(false);
  act(() => result.current.toggleNuclear());
  await waitFor(() => expect(result.current.data).toEqual(data));
  expect(result.current.cablesEnabled).toBe(false);
  expect(result.current.stationsEnabled).toBe(false);
  act(() => result.current.select({ kind: 'nuclear', item: plant }));
  for (const globe of [true, false]) {
    const layers = buildInfrastructureLayers(result.current, vi.fn(), globe);
    expect(layers.map((layer) => layer.id)).toEqual([
      'nuclear-facilities',
      'selected-nuclear-facility-halo',
    ]);
  }
  act(() => result.current.close());
  expect(buildInfrastructureLayers(result.current, vi.fn()).map((layer) => layer.id)).toEqual([
    'nuclear-facilities',
  ]);
  act(() => result.current.select({ kind: 'nuclear', item: plant }));
  act(() => result.current.toggleNuclear());
  expect(result.current.selected).toBeNull();
  expect(buildInfrastructureLayers(result.current, vi.fn())).toEqual([]);
});

it('shows historical capacity, source, country and licence with accurate loaded counts', async () => {
  server.use(http.get('/api/map-infrastructure', () => HttpResponse.json(data)));
  function Harness() {
    const state = useInfrastructure();
    return (
      <>
        <InfrastructurePanel state={state} onSelect={state.select} />
        {state.selected && (
          <InfrastructureInspector
            selected={state.selected}
            onClose={state.close}
            data={state.data}
          />
        )}
      </>
    );
  }
  render(<Harness />);
  fireEvent.click(screen.getByRole('switch', { name: 'Nuclear power facilities' }));
  fireEvent.click(await screen.findByRole('button', { name: /Historical plant/ }));
  expect(screen.getByText(/1 historical nuclear facilities/)).toBeInTheDocument();
  expect(screen.getByText(/1,200 MW.*2017/)).toBeInTheDocument();
  expect(screen.getByText(/does not establish current operating status/)).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Inventory licence' })).toHaveAttribute(
    'href',
    data.nuclear_licence_url,
  );
  fireEvent.click(screen.getByRole('button', { name: 'Close infrastructure details' }));
  expect(screen.queryByLabelText('Infrastructure details')).not.toBeInTheDocument();
});

it('rejects unsafe nuclear URLs and out-of-range fields at the API boundary', () => {
  expect(infrastructureSchema.safeParse(data).success).toBe(true);
  for (const patch of [
    { source_url: 'javascript:alert(1)' },
    { latitude: 91 },
    { capacity_mw: -1 },
    { country_code: 'GB' },
  ]) {
    expect(
      infrastructureSchema.safeParse({ ...data, nuclear_facilities: [{ ...plant, ...patch }] })
        .success,
    ).toBe(false);
  }
});
