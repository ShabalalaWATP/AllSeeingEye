import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import { report } from '@/test/fixtures';
import { applySession } from '@/test/render';
import { mockWebGl2 } from '@/test/env';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import ReportEvidenceMap from './ReportEvidenceMap';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
const evidence = [
  {
    ...report.version.evidence[0]!,
    label: 'E1',
    title: 'Located record',
    geo_confidence: 'exact',
    lon: 10,
    lat: 50,
    published_at: '2026-01-01T12:00:00Z',
  },
  {
    ...report.version.evidence[0]!,
    label: 'E2',
    title: 'Country record',
    geo_confidence: 'country',
    lon: 10,
    lat: 50,
    published_at: '2026-01-02T12:00:00Z',
  },
];
beforeEach(() => {
  applySession('user');
  mockWebGl2(true);
  FakeMap.reset();
  MapboxOverlay.reset();
});

it('loads maps on demand, preserves selection across projections and clears private GPU layers on revocation', async () => {
  render(<ReportEvidenceMap reportId="r" version={2} evidence={evidence} />);
  expect(FakeMap.instances).toHaveLength(0);
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Open evidence map' }));
  // Await the instrumented lazy module, not a hardware-dependent import duration.
  await act(async () => {
    await vi.dynamicImportSettled();
  });
  await screen.findByRole('region', { name: 'Saved evidence globe' });
  await waitFor(() => expect(FakeMap.instances).toHaveLength(1));
  act(() => FakeMap.instances[0]!.fire('style.load'));
  await user.click(screen.getByRole('button', { name: /E1: Located record/ }));
  expect(screen.getByRole('complementary', { name: 'Selected map evidence' })).toHaveTextContent(
    'Located record',
  );
  await user.click(screen.getByRole('button', { name: 'Flat map' }));
  expect(FakeMap.instances[0]!.setProjection).toHaveBeenLastCalledWith({ type: 'mercator' });
  expect(FakeMap.instances).toHaveLength(1);
  expect(screen.getByRole('complementary', { name: 'Selected map evidence' })).toHaveTextContent(
    'Located record',
  );
  const layers = MapboxOverlay.instances[0]!.props.layers as { props: { data: unknown[] } }[];
  expect(layers.flatMap((layer) => layer.props.data)).toEqual([evidence[0]]);
  act(() => invalidateWorkspaceAccess());
  expect(screen.queryByRole('region', { name: 'Saved evidence flat map' })).not.toBeInTheDocument();
  expect(screen.queryByText('Located record')).not.toBeInTheDocument();
  expect(FakeMap.instances[0]!.remove).toHaveBeenCalled();
  expect(MapboxOverlay.instances[0]!.props.layers).toEqual([]);
});

it('filters publication dates without adding live data, and retains unlocated records in the list', async () => {
  render(<ReportEvidenceMap reportId="r" version={2} evidence={evidence} />);
  const user = userEvent.setup();
  await user.selectOptions(screen.getByLabelText('Publication timeline (UTC)'), '2026-01-01');
  expect(
    within(screen.getByRole('list', { name: 'Map evidence' })).queryByText('E2: Country record'),
  ).not.toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText('Publication timeline (UTC)'), '');
  await user.click(screen.getByRole('button', { name: /E2: Country record/ }));
  expect(screen.getByRole('complementary', { name: 'Selected map evidence' })).toHaveTextContent(
    'Country only, not plotted',
  );
  expect(FakeMap.instances).toHaveLength(0);
});

it('disposes the private view on account switch instead of reusing prior evidence', () => {
  render(<ReportEvidenceMap reportId="r" version={2} evidence={evidence} />);
  act(() => applySession('admin'));
  expect(screen.getByRole('status')).toHaveTextContent('Account or access changed');
  expect(screen.queryByRole('list', { name: 'Map evidence' })).not.toBeInTheDocument();
});

it('retains evidence access when WebGL is unavailable', async () => {
  mockWebGl2(false);
  render(<ReportEvidenceMap reportId="r" version={2} evidence={evidence} />);
  await userEvent.setup().click(screen.getByRole('button', { name: 'Open evidence map' }));
  expect(await screen.findByText(/WebGL2 is unavailable/)).toBeVisible();
  expect(screen.getByRole('list', { name: 'Map evidence' })).toHaveTextContent('Country record');
  expect(FakeMap.instances).toHaveLength(0);
});

it('discloses polar limits and leaves original coordinates and selections intact', async () => {
  const polar = [{ ...evidence[0]!, lat: 89 }];
  render(<ReportEvidenceMap reportId="r" version={2} evidence={polar} />);
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Open evidence map' }));
  await screen.findByRole('region', { name: 'Saved evidence globe' });
  await user.click(screen.getByRole('button', { name: 'Flat map' }));
  expect(screen.getByText(/polar records cannot be displayed/)).toBeVisible();
  expect(polar[0]!.lat).toBe(89);
  expect(
    (MapboxOverlay.instances[0]!.props.layers as { props: { data: unknown[] } }[]).flatMap(
      (layer) => layer.props.data,
    ),
  ).toEqual([]);
  await user.click(screen.getByRole('button', { name: 'Globe' }));
  expect(
    (MapboxOverlay.instances[0]!.props.layers as { props: { data: unknown[] } }[]).flatMap(
      (layer) => layer.props.data,
    ),
  ).toEqual(polar);
  act(() => FakeMap.instances[0]!.fire('error'));
  expect(screen.getByText(/basemap could not load completely/)).toBeVisible();
});

it('keeps an empty saved version explicit without manufacturing map evidence', () => {
  render(<ReportEvidenceMap reportId="r" version={2} evidence={[]} />);
  expect(screen.getByText('No saved evidence matches these filters.')).toBeVisible();
});

it('renders a private local overlay in both projections and removes it on access change', async () => {
  render(<ReportEvidenceMap reportId="r" version={2} evidence={evidence} />);
  const user = userEvent.setup();
  await user.click(screen.getByText('Private local GeoJSON overlay'));
  await user.type(screen.getByLabelText('Overlay source'), 'Synthetic local dataset');
  fireEvent.change(screen.getByLabelText('Dataset date'), { target: { value: '2026-09-01' } });
  await user.type(
    screen.getByLabelText('Attribution / licence note'),
    'Synthetic permitted fixture',
  );
  const file = new File(
    [
      JSON.stringify({
        type: 'FeatureCollection',
        features: [
          {
            type: 'Feature',
            properties: { name: 'Local location' },
            geometry: { type: 'Point', coordinates: [40, 30] },
          },
        ],
      }),
    ],
    'local.geojson',
    { type: 'application/geo+json' },
  );
  await user.upload(screen.getByLabelText('Local GeoJSON file'), file);
  expect(await screen.findByRole('list', { name: 'Imported geometry' })).toHaveTextContent(
    'Local location',
  );
  await user.click(screen.getByRole('button', { name: 'Open evidence map' }));
  await screen.findByRole('region', { name: 'Saved evidence globe' });
  const layer = () =>
    (MapboxOverlay.instances[0]!.props.layers as { id: string }[]).find(
      (item) => item.id === 'private-local-geometry',
    );
  await waitFor(() => expect(layer()).toBeDefined());
  await user.click(screen.getByRole('button', { name: 'Flat map' }));
  expect(layer()).toBeDefined();
  await user.click(screen.getByLabelText('Show private overlay'));
  expect(layer()).toBeUndefined();
  await user.click(screen.getByLabelText('Show private overlay'));
  expect(layer()).toBeDefined();
  act(() => invalidateWorkspaceAccess());
  expect(screen.queryByRole('list', { name: 'Imported geometry' })).not.toBeInTheDocument();
  expect(MapboxOverlay.instances[0]!.props.layers).toEqual([]);
});

it('requires declared source metadata before reading a local file', async () => {
  render(<ReportEvidenceMap reportId="r" version={2} evidence={evidence} />);
  const user = userEvent.setup();
  await user.click(screen.getByText('Private local GeoJSON overlay'));
  await user.upload(
    screen.getByLabelText('Local GeoJSON file'),
    new File(['{}'], 'local.geojson', { type: 'application/geo+json' }),
  );
  expect(screen.getByRole('alert')).toHaveTextContent(
    'Enter a source, a valid dataset date and attribution',
  );
  expect(screen.queryByRole('list', { name: 'Imported geometry' })).not.toBeInTheDocument();
});
