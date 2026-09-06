import type { FootprintCollection } from '@/lib/api/footprints';
import type { LocalCollection } from '@/lib/map/geoJsonTypes';
import { parseLocalGeoJson } from '@/lib/map/localGeoJson';

/** Reject unsupported display geometry without discarding its source metadata. */
export function footprintDisplay(result: FootprintCollection): {
  data: LocalCollection;
  omitted: number;
} {
  const data: LocalCollection = { type: 'FeatureCollection', features: [] };
  let omitted = 0;
  for (const [index, feature] of result.features.entries()) {
    try {
      const parsed = parseLocalGeoJson(
        JSON.stringify({
          type: 'FeatureCollection',
          features: [
            { type: 'Feature', geometry: feature.geometry, properties: { name: feature.id } },
          ],
        }),
      );
      data.features.push(...parsed.display.features.map((item) => ({ ...item, id: index })));
    } catch {
      omitted++;
    }
  }
  return { data, omitted };
}
