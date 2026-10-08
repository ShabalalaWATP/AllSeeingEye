import { render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import { rectangleArea } from '@/lib/map/areaGeometry';
import { liveEvent } from '@/test/fixtures.events';
import { describeLivePictureExport, LivePictureExport } from './LivePictureExport';

const area = rectangleArea({ west: 0, east: 2, south: 0, north: 2 });
const inside = liveEvent({ id: 'inside', title: 'Inside event', point: { lon: 1, lat: 1 } });
const outside = liveEvent({ id: 'outside', title: 'Outside event', point: { lon: 5, lat: 1 } });
const approximate = liveEvent({
  id: 'approximate',
  title: 'Approximate event',
  point: { lon: 1, lat: 1 },
  geo_confidence: 'city',
});
const blobs: Blob[] = [];
const downloads: { name: string; href: string }[] = [];
const revoke = vi.fn();
let originalCreate: PropertyDescriptor | undefined;
let originalRevoke: PropertyDescriptor | undefined;

beforeEach(() => {
  blobs.length = 0;
  downloads.length = 0;
  revoke.mockClear();
  originalCreate = Object.getOwnPropertyDescriptor(URL, 'createObjectURL');
  originalRevoke = Object.getOwnPropertyDescriptor(URL, 'revokeObjectURL');
  Object.defineProperty(URL, 'createObjectURL', {
    configurable: true,
    value: (blob: Blob) => {
      blobs.push(blob);
      return `blob:live-export/${blobs.length}`;
    },
  });
  Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revoke });
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
    this: HTMLAnchorElement,
  ) {
    downloads.push({ name: this.download, href: this.href });
  });
});

afterEach(() => {
  if (originalCreate) Object.defineProperty(URL, 'createObjectURL', originalCreate);
  else Reflect.deleteProperty(URL, 'createObjectURL');
  if (originalRevoke) Object.defineProperty(URL, 'revokeObjectURL', originalRevoke);
  else Reflect.deleteProperty(URL, 'revokeObjectURL');
});

function readBlob(blob: Blob): Promise<string> {
  if (typeof blob.text === 'function') return blob.text();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') resolve(reader.result);
      else reject(new Error('Expected text in the exported file.'));
    };
    reader.onerror = () => reject(new Error(reader.error?.message ?? 'Cannot read the export.'));
    reader.readAsText(blob);
  });
}

it('downloads the filtered input sample and records excluded sources without a boundary', async () => {
  render(
    <LivePictureExport
      events={[inside, outside, liveEvent({ source_id: 'unreviewed', id: 'restricted' })]}
      area={null}
    />,
  );
  expect(screen.getByRole('checkbox')).toBeDisabled();
  expect(screen.getByRole('checkbox')).not.toBeChecked();
  await userEvent.setup().click(screen.getByRole('button', { name: 'Download live GeoJSON' }));
  const data = JSON.parse(await readBlob(blobs[0]!)) as {
    features: { id: string }[];
    metadata: { excluded_sources: { source: string }[] };
  };
  expect(data.features.map((feature) => feature.id)).toEqual(['inside', 'outside']);
  expect(data.metadata.excluded_sources[0]?.source).toBe('unreviewed');
  expect(blobs[0]?.type).toBe('application/geo+json');
  expect(downloads).toEqual([
    { name: 'filtered-live-picture.geojson', href: 'blob:live-export/1' },
  ]);
  await waitFor(() => expect(revoke).toHaveBeenCalledWith('blob:live-export/1'));
});

it('restricts KML to exact and explicitly uncertain matches inside the research boundary', async () => {
  render(<LivePictureExport events={[inside, outside, approximate]} area={area} />);
  const user = userEvent.setup();
  await user.click(screen.getByRole('checkbox'));
  expect(screen.getByRole('checkbox')).toBeChecked();
  await user.click(screen.getByRole('button', { name: 'Download live KML' }));
  const xml = new DOMParser().parseFromString(await readBlob(blobs[0]!), 'application/xml');
  expect(xml.querySelector('parsererror')).toBeNull();
  expect([...xml.querySelectorAll('Placemark > name')].map((node) => node.textContent)).toEqual([
    'Inside event',
    'Approximate event',
  ]);
  expect(xml.querySelectorAll('Data[name="representative_location"] value')[1]?.textContent).toBe(
    'true',
  );
  expect(blobs[0]?.type).toBe('application/vnd.google-earth.kml+xml');
  expect(downloads[0]?.name).toBe('filtered-live-picture.kml');
  await waitFor(() => expect(revoke).toHaveBeenCalledWith('blob:live-export/1'));
});

it('shows the eligible feature and excluded source counts', () => {
  render(
    <LivePictureExport
      events={[inside, outside, liveEvent({ source_id: 'unreviewed', id: 'restricted' })]}
      area={null}
    />,
  );
  const summary = screen.getByText(/will be exported/);
  expect(summary).toHaveTextContent('2 eligible features will be exported. 1 source excluded.');
  const geojson = screen.getByRole('button', { name: 'Download live GeoJSON' });
  expect(geojson).toBeEnabled();
  expect(geojson).toHaveAccessibleDescription(summary.textContent);
});

it('disables both downloads and explains why when nothing is eligible', async () => {
  render(
    <LivePictureExport
      events={[
        liveEvent({ source_id: 'unreviewed', id: 'one' }),
        liveEvent({ source_id: 'cisa_kev', id: 'two' }),
      ]}
      area={null}
    />,
  );
  expect(screen.getByText(/Nothing to export/)).toHaveTextContent('2 sources excluded.');
  const geojson = screen.getByRole('button', { name: 'Download live GeoJSON' });
  expect(geojson).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Download live KML' })).toBeDisabled();
  await userEvent.setup().click(geojson);
  expect(blobs).toHaveLength(0);
});

it('describes singular counts and a truncated export', () => {
  const base = { canDownload: true, excludedSourceCount: 0 };
  expect(describeLivePictureExport({ ...base, featureCount: 1, eligibleCount: 1 })).toBe(
    '1 eligible feature will be exported. 0 sources excluded.',
  );
  expect(
    describeLivePictureExport({
      ...base,
      featureCount: 5000,
      eligibleCount: 5001,
      excludedSourceCount: 1,
    }),
  ).toBe(
    '5,000 eligible features will be exported (limited from 5,001 eligible). 1 source excluded.',
  );
});

it('exports the current full sample if a previously selected boundary is removed', async () => {
  const { rerender } = render(<LivePictureExport events={[inside, outside]} area={area} />);
  const user = userEvent.setup();
  await user.click(screen.getByRole('checkbox'));
  rerender(<LivePictureExport events={[outside]} area={null} />);
  expect(screen.getByRole('checkbox')).toBeDisabled();
  expect(screen.getByRole('checkbox')).not.toBeChecked();
  await user.click(screen.getByRole('button', { name: 'Download live GeoJSON' }));
  const data = JSON.parse(await readBlob(blobs[0]!)) as { features: { id: string }[] };
  expect(data.features.map((feature) => feature.id)).toEqual(['outside']);
  await waitFor(() => expect(revoke).toHaveBeenCalledWith('blob:live-export/1'));
});
