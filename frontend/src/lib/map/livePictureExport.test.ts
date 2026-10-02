import { expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { exportLivePicture, livePictureCollection } from './livePictureExport';

it('exports reviewed metadata only and records all excluded source identifiers', () => {
  const allowed = liveEvent({
    source_id: 'usgs_earthquakes',
    attributes: { secret: 'not exported' },
  });
  const result = livePictureCollection([
    allowed,
    liveEvent({ source_id: 'unreviewed' }),
    liveEvent({ source_id: '__proto__' }),
  ]);
  expect(result.features).toHaveLength(1);
  expect(result.metadata.excluded_sources.map((item) => item.source)).toEqual([
    '__proto__',
    'unreviewed',
  ]);
  expect(result.features[0]?.properties.attribution).toContain('Geological Survey');
  expect(JSON.stringify(result)).not.toContain('not exported');
});

it('bounds exports at 5000 and preserves approximate location semantics', () => {
  const event = liveEvent({ source_id: 'firms_public_noaa20', geo_confidence: 'city' });
  const result = livePictureCollection(
    Array.from({ length: 5001 }, (_, id) => ({ ...event, id: String(id) })),
  );
  expect(result.features).toHaveLength(5000);
  expect(result.metadata.truncated).toBe(true);
  expect(result.features[0]?.properties).toMatchObject({
    location_precision: 'city',
    representative_location: true,
  });
});

it('omits unknown or invalid locations and credential-bearing URLs', () => {
  const base = liveEvent({ source_id: 'usgs_earthquakes', url: 'https://user:pass@example.org' });
  const result = livePictureCollection([
    base,
    { ...base, point: null },
    { ...base, point: { lat: NaN, lon: 1 } },
    { ...base, geo_confidence: 'none' },
  ]);
  expect(result.features).toHaveLength(1);
  expect(result.features[0]?.properties.url).toBeNull();
  expect(result.metadata.omitted_locations).toBe(3);
});

it('escapes KML data without introducing markup or losing attribution and exclusions', () => {
  const text = exportLivePicture(
    [
      liveEvent({ source_id: 'usgs_earthquakes', title: '<script>&"quoted"\u0001' }),
      liveEvent({ source_id: 'restricted' }),
    ],
    'kml',
  );
  const doc = new DOMParser().parseFromString(text, 'application/xml');
  expect(doc.querySelector('parsererror')).toBeNull();
  expect(doc.querySelector('script')).toBeNull();
  expect(doc.querySelector('Placemark name')?.textContent).toBe('<script>&"quoted"');
  expect(text).toContain('Geological Survey');
  expect(text).toContain('restricted');
});

it('removes invalid XML characters while preserving supplementary-plane text', () => {
  const title = 'Data\uFFFE\uFFFF\uD800-\uDC00: \u{1F30D} \u{10437}';
  const text = exportLivePicture([liveEvent({ source_id: 'usgs_earthquakes', title })], 'kml');
  const doc = new DOMParser().parseFromString(text, 'application/xml');
  expect(doc.querySelector('parsererror')).toBeNull();
  expect(doc.querySelector('Placemark name')?.textContent).toBe('Data-: \u{1F30D} \u{10437}');
  expect(doc.querySelector('Data[name="title"] value')?.textContent).toBe(
    'Data-: \u{1F30D} \u{10437}',
  );
});
