import { z } from 'zod';
import { scopedMutation } from '@/lib/workspaceAccess';
import { apiCall, apiSend } from './client';
import type { components } from './types.gen';

const geometry = z.record(z.string(), z.unknown());
export const mapStateSchema = z.object({
  camera: z.object({
    longitude: z.number().min(-180).max(180),
    latitude: z.number().min(-90).max(90),
    zoom: z.number().min(0).max(22),
    bearing: z.number().min(-180).max(180).default(0),
    pitch: z.number().min(0).max(60).default(0),
  }),
  projection: z.enum(['globe', 'mercator']).default('globe'),
  basemap: z
    .enum(['dark', 'streets', 'light', 'satellite', 'hybrid', 'os_road', 'os_outdoor', 'os_light'])
    .default('dark'),
  source_ids: z.array(z.string()).max(64).default([]),
  published_since: z.string().nullable().default(null),
  published_until: z.string().nullable().default(null),
  include_unknown_dates: z.boolean().default(true),
  time_basis: z
    .enum(['publication', 'acquisition_or_publication', 'recorded_time'])
    .default('publication'),
  selected_evidence: z.string().nullable().default(null),
  overlays: z
    .array(
      z.object({
        geometry,
        source: z.string(),
        dataset_date: z.string(),
        attribution: z.string(),
        precision: z.enum(['exact', 'approximate', 'unknown']),
        visible: z.boolean().default(true),
      }),
    )
    .max(8)
    .default([]),
  aoi: geometry.nullable().default(null),
  schema_version: z.literal(1).default(1),
  display_transform: z
    .enum(['ase-geojson-display-v1', 'ase-geojson-display-v2'])
    .default('ase-geojson-display-v1'),
}) satisfies z.ZodType<components['schemas']['MapStateFields']>;
const viewSchema = z.object({
  id: z.string(),
  report_id: z.string(),
  created_by: z.string(),
  team_id: z.string().nullable(),
  latest_revision_id: z.string(),
  created_at: z.string(),
  archived: z.boolean(),
});
export const savedMapSchema = z.object({
  view: viewSchema,
  revision: z.object({
    id: z.string(),
    view_id: z.string(),
    number: z.number().int().positive(),
    title: z.string(),
    report_version_id: z.string(),
    report_version_number: z.number().int().positive(),
    state: mapStateSchema,
    evidence_sha256: z.string(),
    content_sha256: z.string(),
    created_by: z.string(),
    created_at: z.string(),
  }),
}) satisfies z.ZodType<components['schemas']['SavedMapViewOut']>;
const pageSchema = z.object({
  items: z.array(
    z.object({
      view: viewSchema,
      title: z.string(),
      revision_number: z.number(),
      report_version_number: z.number(),
      updated_at: z.string(),
    }),
  ),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
}) satisfies z.ZodType<components['schemas']['MapViewPageOut']>;
export type MapState = z.infer<typeof mapStateSchema>;
export type SavedMapView = z.infer<typeof savedMapSchema>;
export type MapViewPage = z.infer<typeof pageSchema>;
const base = '/api/map/views';
export function listMapViews(reportId: string, offset: number, signal: AbortSignal) {
  return apiCall(`${base}?report_id=${encodeURIComponent(reportId)}&limit=20&offset=${offset}`, {
    schema: pageSchema,
    signal,
  });
}
export function fetchMapView(id: string, revision: string, signal: AbortSignal) {
  return apiCall(`${base}/${encodeURIComponent(id)}/revisions/${encodeURIComponent(revision)}`, {
    schema: savedMapSchema,
    signal,
  });
}
export function createMapView(body: components['schemas']['MapViewCreateIn'], signal: AbortSignal) {
  return scopedMutation(() =>
    apiCall(base, { method: 'POST', body, schema: savedMapSchema, signal }),
  );
}
export function updateMapView(
  id: string,
  body: components['schemas']['MapViewUpdateIn'],
  signal: AbortSignal,
) {
  return scopedMutation(() =>
    apiCall(`${base}/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body,
      schema: savedMapSchema,
      signal,
    }),
  );
}
export function archiveMapView(id: string, signal: AbortSignal) {
  return scopedMutation(() =>
    apiSend(`${base}/${encodeURIComponent(id)}`, { method: 'DELETE', signal }),
  );
}
