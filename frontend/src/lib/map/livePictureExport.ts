/** Local serialisation of the already filtered map sample; never fetches or stores events. */
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { LIVE_EXPORT_TERMS } from './liveExportTerms';

export const MAX_LIVE_EXPORT_EVENTS = 5_000;

function safeUrl(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password
      ? url.href
      : null;
  } catch {
    return null;
  }
}

export function livePictureCollection(events: readonly LiveEvent[]) {
  const excluded = new Set<string>();
  const attributed = new Set<string>();
  const features = [];
  let omittedLocations = 0;
  let eligible = 0;
  for (const event of events) {
    const terms = Object.hasOwn(LIVE_EXPORT_TERMS, event.source_id)
      ? LIVE_EXPORT_TERMS[event.source_id]
      : undefined;
    if (!terms) {
      excluded.add(event.source_id);
      continue;
    }
    const point = event.point;
    if (
      !point ||
      !Number.isFinite(point.lon) ||
      !Number.isFinite(point.lat) ||
      Math.abs(point.lon) > 180 ||
      Math.abs(point.lat) > 90 ||
      event.geo_confidence === 'none'
    ) {
      omittedLocations++;
      continue;
    }
    eligible++;
    if (features.length >= MAX_LIVE_EXPORT_EVENTS) continue;
    attributed.add(event.source_id);
    features.push({
      type: 'Feature' as const,
      id: event.id,
      geometry: { type: 'Point' as const, coordinates: [point.lon, point.lat] },
      properties: {
        id: event.id,
        title: event.title,
        time: event.published_at,
        source: event.source_id,
        grade: event.grade,
        location_precision: event.geo_confidence,
        representative_location: event.geo_confidence !== 'exact',
        url: safeUrl(event.url),
        attribution: terms.attribution,
      },
    });
  }
  return {
    type: 'FeatureCollection' as const,
    metadata: {
      sample: 'Already loaded map events after current filters; not complete provider coverage.',
      precision: 'Non-exact coordinates are representative locations, not exact observations.',
      limit: MAX_LIVE_EXPORT_EVENTS,
      eligible_count: eligible,
      truncated: eligible > MAX_LIVE_EXPORT_EVENTS,
      omitted_locations: omittedLocations,
      excluded_sources: [...excluded].sort().map((source) => ({
        source,
        reason: 'Redistribution of this metadata has not been approved in the reviewed mapping.',
      })),
      attribution: [...attributed]
        .sort()
        .map((source) => ({ source, ...LIVE_EXPORT_TERMS[source] })),
    },
    features,
  };
}

function xml(value: unknown): string {
  const plain =
    typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'
      ? String(value)
      : '';
  return Array.from(plain)
    .filter((char) => {
      const code = char.codePointAt(0) ?? 0;
      // XML 1.0 Char excludes lone surrogates and U+FFFE/U+FFFF.
      return (
        [9, 10, 13].includes(code) ||
        (code >= 0x20 && code <= 0xd7ff) ||
        (code >= 0xe000 && code <= 0xfffd) ||
        (code >= 0x10000 && code <= 0x10ffff)
      );
    })
    .join('')
    .replace(
      /[<>&"']/g,
      (char) =>
        ({
          '<': '&lt;',
          '>': '&gt;',
          '&': '&amp;',
          '"': '&quot;',
          "'": '&apos;',
        })[char] ?? char,
    );
}

export function exportLivePicture(events: readonly LiveEvent[], format: 'geojson' | 'kml'): string {
  const collection = livePictureCollection(events);
  if (format === 'geojson') return JSON.stringify(collection, null, 2);
  const placemarks = collection.features
    .map((feature) => {
      const fields = Object.entries(feature.properties)
        .map(([name, value]) => `<Data name="${xml(name)}"><value>${xml(value)}</value></Data>`)
        .join('');
      return (
        `<Placemark><name>${xml(feature.properties.title)}</name><ExtendedData>${fields}</ExtendedData>` +
        `<Point><coordinates>${feature.geometry.coordinates.join(',')},0</coordinates></Point></Placemark>`
      );
    })
    .join('');
  return (
    '<?xml version="1.0" encoding="UTF-8"?>' +
    '<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Filtered live picture</name>' +
    `<ExtendedData><Data name="metadata"><value>${xml(JSON.stringify(collection.metadata))}</value></Data></ExtendedData>` +
    placemarks +
    '</Document></kml>'
  );
}
