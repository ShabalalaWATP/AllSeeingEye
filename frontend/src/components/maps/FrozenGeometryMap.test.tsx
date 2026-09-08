import { act, render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import { report } from '@/test/fixtures';
import { applySession } from '@/test/render';
import { mockWebGl2 } from '@/test/env';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import type { LocalCollection, LocalFeature } from '@/lib/map/geoJsonTypes';
import type { EvidenceItem } from '@/lib/api/reports';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import ReportEvidenceMap from './ReportEvidenceMap';
import * as preparation from './frozenEvidenceGeometry';
import * as topology from '@/lib/map/geoJsonTopology';
import { savedMapFixture } from '@/test/fixtures.savedMaps';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
beforeEach(() => {
  applySession('user');
  mockWebGl2(true);
  FakeMap.reset();
  MapboxOverlay.reset();
});
const ring = Array.from({ length: 300 }, (_, i) => [
  Math.cos((i * 2 * Math.PI) / 300),
  Math.sin((i * 2 * Math.PI) / 300),
]);
ring.push(ring[0]!);
const item: EvidenceItem = {
  ...report.version.evidence[0]!,
  label: 'E1',
  title: 'Frozen scene',
  published_at: null,
  lon: null,
  lat: null,
  geometry: {
    geometry: { type: 'Polygon', coordinates: [ring] },
    sha256: 'frozen',
    location_role: 'observation_footprint',
    precision: 'Scene coverage',
    method: 'Catalogue',
    source_id: 'catalogue',
    attribution: 'Copernicus',
  },
};

it('prepares saved overlays and the area within one shared topology budget', () => {
  const budget = vi.spyOn(topology, 'topologyBudget');
  const saved = {
    ...savedMapFixture,
    revision: {
      ...savedMapFixture.revision,
      state: {
        ...savedMapFixture.revision.state,
        overlays: Array.from({ length: 8 }, () => ({
          ...savedMapFixture.revision.state.overlays[0]!,
          visible: true,
        })),
      },
    },
  };
  render(
    <ReportEvidenceMap
      reportId={saved.view.report_id}
      version={saved.revision.report_version_number}
      savedView={saved}
      evidence={[item]}
    />,
  );
  expect(budget).toHaveBeenCalledTimes(1);
});

it('keeps legacy saved maps point-only until the operator explicitly upgrades the display', async () => {
  const user = userEvent.setup();
  const saved = {
    ...savedMapFixture,
    revision: {
      ...savedMapFixture.revision,
      state: { ...savedMapFixture.revision.state, include_unknown_dates: true },
    },
  };
  render(
    <ReportEvidenceMap
      reportId={saved.view.report_id}
      version={saved.revision.report_version_number}
      savedView={saved}
      evidence={[item]}
    />,
  );
  expect(screen.getByText(/0 supported source geometries/)).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Include source footprints' }));
  expect(screen.getByText(/1 supported source geometries/)).toBeInTheDocument();
  expect(saved.revision.state.display_transform).toBe('ase-geojson-display-v1');
});
function layer() {
  const layers = MapboxOverlay.instances[0]!.props.layers as {
    props: {
      id: string;
      data: LocalCollection;
      onClick: (info: { object: LocalFeature }) => void;
    };
  }[];
  return layers.find((entry) => entry.props.id === 'frozen-evidence-geometry')!.props;
}
it('renders and selects retained geometry in both projections, fits only on selection and clears access', async () => {
  const prepare = vi.spyOn(preparation, 'prepareEvidenceGeometry');
  const user = userEvent.setup();
  render(<ReportEvidenceMap reportId="report" version={1} evidence={[item]} />);
  await user.click(screen.getByRole('button', { name: 'Open evidence map' }));
  await act(async () => {
    await vi.dynamicImportSettled();
  });
  await screen.findByRole('region', { name: 'Saved evidence globe' });
  await waitFor(() => expect(FakeMap.instances).toHaveLength(1));
  act(() => FakeMap.instances[0]!.fire('style.load'));
  expect(layer().data.features[0]?.geometry).toEqual(item.geometry?.geometry);
  expect(FakeMap.instances[0]!.fitBounds).not.toHaveBeenCalled();
  const preparationCount = prepare.mock.calls.length;
  act(() => FakeMap.instances[0]!.fire('moveend'));
  expect(prepare).toHaveBeenCalledTimes(preparationCount);
  await user.click(screen.getByRole('button', { name: /E1: Frozen scene/ }));
  expect(FakeMap.instances[0]!.fitBounds).toHaveBeenCalledTimes(1);
  expect(prepare).toHaveBeenCalledTimes(preparationCount);
  await user.click(screen.getByRole('button', { name: 'Flat map' }));
  expect(layer().data.features[0]?.geometry).toEqual(item.geometry?.geometry);
  expect(FakeMap.instances[0]!.fitBounds).toHaveBeenCalledTimes(1);
  act(() => layer().onClick({ object: layer().data.features[0]! }));
  expect(screen.getByRole('complementary', { name: 'Selected map evidence' })).toHaveTextContent(
    'Frozen scene',
  );
  act(() => invalidateWorkspaceAccess());
  expect(MapboxOverlay.instances[0]!.props.layers).toEqual([]);
  expect(FakeMap.instances[0]!.remove).toHaveBeenCalled();
});
