import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { parseLocalGeoJson } from '@/lib/map/localGeoJson';
import { LocalGeoJsonOverlay } from './LocalGeoJsonOverlay';

class ControlledReader {
  static latest: ControlledReader;
  static created = 0;
  result: string | ArrayBuffer | null = null;
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  abort = vi.fn();
  readAsText = vi.fn();
  constructor() {
    ControlledReader.latest = this;
    ControlledReader.created++;
  }
}

beforeEach(() => {
  ControlledReader.created = 0;
  vi.stubGlobal('FileReader', ControlledReader);
});
afterEach(() => vi.unstubAllGlobals());

async function mount() {
  const onChange = vi.fn();
  const onVisible = vi.fn();
  const mounted = render(
    <LocalGeoJsonOverlay
      overlay={null}
      visible={false}
      onChange={onChange}
      onVisible={onVisible}
    />,
  );
  const user = userEvent.setup();
  await user.click(screen.getByText('Private local GeoJSON overlay'));
  fireEvent.change(screen.getByLabelText('Overlay source'), { target: { value: 'Local survey' } });
  fireEvent.change(screen.getByLabelText('Dataset date'), { target: { value: '2026-09-01' } });
  fireEvent.change(screen.getByLabelText('Attribution / licence note'), {
    target: { value: 'Survey team' },
  });
  const select = (file: File) =>
    fireEvent.change(screen.getByLabelText('Local GeoJSON file'), { target: { files: [file] } });
  return { ...mounted, onChange, onVisible, user, select };
}

it('rejects oversized and unsupported files before reading them', async () => {
  const { select, onChange } = await mount();
  const oversized = new File(['{}'], 'survey.geojson');
  Object.defineProperty(oversized, 'size', { value: 5 * 1024 * 1024 + 1 });
  select(oversized);
  expect(screen.getByRole('alert')).toHaveTextContent('GeoJSON is limited to 5 MiB');
  select(new File(['{}'], 'survey.txt'));
  expect(screen.getByRole('alert')).toHaveTextContent('Select a local .geojson or .json file');
  expect(onChange).not.toHaveBeenCalled();
  expect(ControlledReader.created).toBe(0);
  fireEvent.change(screen.getByLabelText('Local GeoJSON file'), { target: { files: [] } });
  expect(onChange).not.toHaveBeenCalled();
});

it.each(['{broken', new ArrayBuffer(1)])(
  'reports malformed or non-text reads without replacing the overlay',
  async (result) => {
    const { select, onChange, onVisible } = await mount();
    select(new File(['{}'], 'survey.geojson'));
    expect(screen.getByLabelText('Local GeoJSON file')).toBeDisabled();
    act(() => {
      ControlledReader.latest.result = result;
      ControlledReader.latest.onload?.();
    });
    expect(screen.getByRole('alert')).toHaveTextContent('The file is not valid JSON');
    expect(onChange).not.toHaveBeenCalled();
    expect(onVisible).not.toHaveBeenCalled();
    expect(screen.getByLabelText('Local GeoJSON file')).toBeEnabled();
  },
);

it('shows parser validation errors and file read errors, then permits another selection', async () => {
  const { select, onChange } = await mount();
  select(new File(['{}'], 'survey.geojson'));
  act(() => {
    ControlledReader.latest.result = '{}';
    ControlledReader.latest.onload?.();
  });
  expect(screen.getByRole('alert')).toHaveTextContent('Import a GeoJSON FeatureCollection.');
  expect(onChange).not.toHaveBeenCalled();
  select(new File(['{}'], 'survey.geojson'));
  act(() => ControlledReader.latest.onerror?.());
  expect(screen.getByRole('alert')).toHaveTextContent('The local file could not be read');
  expect(screen.getByLabelText('Local GeoJSON file')).toBeEnabled();
});

it('aborts on unmount and ignores late success and failure callbacks', async () => {
  const { select, onChange, onVisible, unmount } = await mount();
  select(new File(['{}'], 'survey.geojson'));
  const reader = ControlledReader.latest;
  unmount();
  expect(reader.abort).toHaveBeenCalledOnce();
  act(() => {
    reader.result = '{}';
    reader.onload?.();
    reader.onerror?.();
  });
  expect(onChange).not.toHaveBeenCalled();
  expect(onVisible).not.toHaveBeenCalled();
});

it('displays retained metadata when local geometry is unavailable and allows hiding or removal', async () => {
  const onChange = vi.fn();
  const onVisible = vi.fn();
  render(
    <LocalGeoJsonOverlay
      overlay={null}
      visible
      onChange={onChange}
      onVisible={onVisible}
      retained={{
        source: 'Retained survey',
        dataset_date: '2026-09-01',
        attribution: 'Local licence',
        precision: 'approximate',
      }}
    />,
  );
  const user = userEvent.setup();
  await user.click(screen.getByText('Private local GeoJSON overlay'));
  expect(screen.getByText(/Retained survey/)).toHaveTextContent('approximate precision');
  expect(screen.getByText('Local licence')).toBeVisible();
  expect(screen.getByRole('list', { name: 'Imported geometry' })).toBeEmptyDOMElement();
  await user.click(screen.getByLabelText('Show private overlay'));
  expect(onVisible).toHaveBeenCalledWith(false);
  await user.click(screen.getByRole('button', { name: 'Remove local overlay' }));
  expect(onChange).toHaveBeenCalledWith(null);
});

it('pages imported geometry and clamps the page when a shorter overlay replaces it', async () => {
  const geometry = parseLocalGeoJson(
    JSON.stringify({
      type: 'FeatureCollection',
      features: Array.from({ length: 21 }, (_, index) => ({
        type: 'Feature',
        properties: { label: `Survey point ${index}` },
        geometry: { type: 'Point', coordinates: [index, 10] },
      })),
    }),
  );
  const overlay = {
    ...geometry,
    source: 'Survey',
    datasetDate: '2026-09-01',
    attribution: 'Survey team',
    precision: 'approximate' as const,
  };
  const callbacks = { onChange: vi.fn(), onVisible: vi.fn() };
  const { rerender } = render(<LocalGeoJsonOverlay {...callbacks} overlay={overlay} visible />);
  const user = userEvent.setup();
  await user.click(screen.getByText('Private local GeoJSON overlay'));
  const items = () => within(screen.getByRole('list', { name: 'Imported geometry' }));
  expect(items().getAllByRole('listitem')).toHaveLength(20);
  expect(screen.getByRole('button', { name: 'Previous geometry' })).toBeDisabled();
  await user.click(screen.getByRole('button', { name: 'Next geometry' }));
  expect(items().getAllByRole('listitem')).toHaveLength(1);
  expect(items().getByText('Survey point 20 · Point')).toBeVisible();
  expect(screen.getByRole('button', { name: 'Next geometry' })).toBeDisabled();
  await user.click(screen.getByRole('button', { name: 'Previous geometry' }));
  expect(items().getAllByRole('listitem')).toHaveLength(20);
  await user.click(screen.getByRole('button', { name: 'Next geometry' }));
  rerender(
    <LocalGeoJsonOverlay
      {...callbacks}
      overlay={{
        ...overlay,
        canonical: { ...overlay.canonical, features: overlay.canonical.features.slice(0, 1) },
      }}
      visible
    />,
  );
  expect(items().getByText('Survey point 0 · Point')).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Next geometry' })).not.toBeInTheDocument();
});
