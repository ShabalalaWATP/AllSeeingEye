import { z } from 'zod';

export const evidenceGeometrySchema = z.object({
  geometry: z.object({
    type: z.enum([
      'Point',
      'MultiPoint',
      'LineString',
      'MultiLineString',
      'Polygon',
      'MultiPolygon',
    ]),
    coordinates: z.array(z.json()),
  }),
  sha256: z.string(),
  location_role: z.enum([
    'incident',
    'reported_area',
    'registered_office',
    'project_site',
    'publisher_location',
    'observation_footprint',
    'analyst_annotation',
  ]),
  precision: z.string(),
  method: z.string(),
  source_id: z.string(),
  attribution: z.string(),
});

export const observationSchema = z.object({
  acquired_at: z.string(),
  processed_at: z.string().nullable(),
  collection_id: z.string(),
  item_id: z.string(),
  limitations: z.string(),
  scene_cloud_cover: z.number().min(0).max(100).nullable(),
});
