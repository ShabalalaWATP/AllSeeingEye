import { act, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { PathLayer, IconLayer } from '@deck.gl/layers';
import * as api from '@/lib/api/infrastructure';
import type { Cable, GroundStation, Infrastructure } from '@/lib/api/infrastructure';
import type { GlobeEngineHandle } from '../useGlobeEngine';
import { useInfrastructure } from './useInfrastructure';
import { useInfrastructureSelection } from './useInfrastructureSelection';
import { buildInfrastructureLayers } from './infrastructureLayers';
import { InfrastructurePanel } from './InfrastructurePanel';
import { InfrastructureInspector } from './InfrastructureInspector';

const cable: Cable = {
  id: 'c',
  name: 'Cable',
  category: 'telecom',
  path: [
    [179, 0],
    [-179, 1],
  ],
  source_url: 'https://www.openstreetmap.org/way/1',
  note: 'Approximate route.',
};
const station: GroundStation = {
  id: 's',
  name: 'Station',
  operator: 'ESA',
  country: 'SE',
  longitude: 20,
  latitude: 67,
  source_url: 'https://esa.int/',
  note: 'Approximate location.',
};
const data: Infrastructure = {
  energy_sites: [],
  semiconductor_sites: [],
  site_attribution: 'Wikidata and OpenStreetMap contributors',
  site_licence_url: 'https://www.openstreetmap.org/copyright',
  site_snapshot_date: '2026-09-13',
  data_centres: [],
  data_centre_attribution: 'OpenStreetMap contributors',
  data_centre_licence_url: 'https://www.openstreetmap.org/copyright',
  data_centre_snapshot_date: '2026-09-13',
  cables: [cable],
  ground_stations: [station],
  snapshot_date: '2026-09-08',
  cable_attribution: 'OSM contributors',
  cable_licence_url: 'https://www.openstreetmap.org/copyright',
  nuclear_facilities: [],
  nuclear_attribution: 'WRI historical inventory',
  nuclear_licence_url: 'https://creativecommons.org/licenses/by/4.0/',
  nuclear_dataset_version: '1.3.0',
  nuclear_snapshot_date: '2026-09-09',
};
afterEach(() => vi.restoreAllMocks());

it.each(['resolve', 'reject'] as const)(
  'ignores a late %s after disabling the final layer',
  async (outcome) => {
    let settle: (value: Infrastructure) => void = () => undefined;
    let fail: (error: Error) => void = () => undefined;
    const pending = new Promise<Infrastructure>((resolve, reject) => {
      settle = resolve;
      fail = reject;
    });
    const request = vi.spyOn(api, 'fetchInfrastructure').mockReturnValue(pending);
    const { result, unmount } = renderHook(() => useInfrastructure());
    act(() => result.current.toggleCables());
    expect(result.current.loading).toBe(true);
    act(() => result.current.toggleCables());
    expect(request.mock.calls[0]?.[0].aborted).toBe(true);
    await act(async () => {
      if (outcome === 'resolve') settle(data);
      else fail(new Error('late failure'));
      await pending.catch(() => undefined);
    });
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.loading).toBe(false);
    unmount();
  },
);

it('aborts an outstanding request on unmount', () => {
  const request = vi
    .spyOn(api, 'fetchInfrastructure')
    .mockReturnValue(new Promise(() => undefined));
  const { result, unmount } = renderHook(() => useInfrastructure());
  act(() => result.current.toggleStations());
  unmount();
  expect(request.mock.calls[0]?.[0].aborted).toBe(true);
});

it('uses larger white cable highlights and restores normal appearance after clearing selection', () => {
  const base = { data, cablesEnabled: true, stationsEnabled: true, selected: null };
  const normal = buildInfrastructureLayers(base, vi.fn());
  const selected = buildInfrastructureLayers(
    { ...base, selected: { kind: 'cable', item: cable } },
    vi.fn(),
  );
  const getWidth = (layer: unknown) =>
    (layer as PathLayer<Cable>).props.getWidth as (item: Cable) => number;
  const getColor = (layer: unknown) =>
    (layer as PathLayer<Cable>).props.getColor as unknown as (item: Cable) => number[];
  expect(getWidth(selected[0])(cable)).toBeGreaterThan(getWidth(normal[0])(cable));
  expect(getColor(selected[0])(cable)).toEqual([255, 255, 255, 255]);
  expect(getColor(normal[0])(cable)).not.toEqual(getColor(selected[0])(cable));
  expect(getWidth(selected[0])({ ...cable, id: 'other' })).toBe(getWidth(normal[0])(cable));
  const selectedStation = buildInfrastructureLayers(
    { ...base, selected: { kind: 'station', item: station } },
    vi.fn(),
  );
  const getSize = (layer: unknown) =>
    (layer as IconLayer<GroundStation>).props.getSize as (item: GroundStation) => number;
  expect(getSize(selectedStation[1])(station)).toBeGreaterThan(getSize(normal[1])(station));
});

it('blocks map and list selection during measurement and focuses valid locations afterwards', async () => {
  vi.spyOn(api, 'fetchInfrastructure').mockResolvedValue(data);
  const closeOther = vi.fn();
  const flyTo = vi.fn();
  const engine = { flyTo } as unknown as GlobeEngineHandle;
  const { result, rerender } = renderHook(
    ({ picking }) => {
      const state = useInfrastructure();
      return { state, ...useInfrastructureSelection(state, picking, closeOther, engine, 'map') };
    },
    { initialProps: { picking: true } },
  );
  act(() => {
    result.current.state.toggleCables();
    result.current.state.toggleStations();
  });
  await waitFor(() => expect(result.current.layers).toHaveLength(2));
  act(() => result.current.focus({ kind: 'station', item: station }));
  const click = result.current.layers[0]?.props.onClick as (info: unknown) => void;
  act(() => click({ object: cable }));
  expect(closeOther).not.toHaveBeenCalled();
  expect(flyTo).not.toHaveBeenCalled();
  rerender({ picking: false });
  act(() => result.current.focus({ kind: 'station', item: station }));
  expect(flyTo).toHaveBeenLastCalledWith({ center: [20, 67], zoom: 8 });
  act(() => result.current.focus({ kind: 'cable', item: cable }));
  expect(flyTo).toHaveBeenLastCalledWith({ center: [179, 0], zoom: 4 });
  expect(closeOther).toHaveBeenCalledTimes(2);
  act(() => result.current.focus({ kind: 'cable', item: { ...cable, path: [] } }));
  expect(flyTo).toHaveBeenCalledTimes(2);
});

it('renders retry, bounded search results and lets country searches find ground stations', async () => {
  vi.spyOn(api, 'fetchInfrastructure')
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValue({
      ...data,
      cables: Array.from({ length: 51 }, (_, i) => ({
        ...cable,
        id: String(i),
        name: `Cable ${i}`,
      })),
    });
  function Panel() {
    const state = useInfrastructure();
    return <InfrastructurePanel state={state} onSelect={state.select} />;
  }
  const user = userEvent.setup();
  render(<Panel />);
  await user.click(screen.getByRole('switch', { name: 'Undersea cables' }));
  await user.click(await screen.findByRole('button', { name: 'Retry infrastructure' }));
  await screen.findByText(/Showing the first 50 of 51/);
  await user.click(screen.getByRole('switch', { name: 'Satellite ground stations' }));
  await user.type(screen.getByRole('searchbox'), 'SE');
  expect(screen.getByRole('button', { name: /Station/ })).toBeInTheDocument();
  expect(screen.queryByText(/Showing the first 50/)).not.toBeInTheDocument();
});

it('respects consumed Escape and restores the launching control on inspector unmount', () => {
  const opener = document.createElement('button');
  document.body.append(opener);
  opener.focus();
  const close = vi.fn();
  const { unmount } = render(
    <InfrastructureInspector selected={{ kind: 'station', item: station }} onClose={close} />,
  );
  fireEvent.keyDown(window, { key: 'Enter' });
  const consumed = new KeyboardEvent('keydown', { key: 'Escape', cancelable: true });
  consumed.preventDefault();
  window.dispatchEvent(consumed);
  expect(close).not.toHaveBeenCalled();
  unmount();
  expect(opener).toHaveFocus();
  opener.remove();
});
