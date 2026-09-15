import { z } from 'zod';

import { apiCall } from './client';
import { categorySchema } from './eventSchemas';
import type { components } from './types.gen';

export const sourceRatingSchema = z.object({
  policy_version: z.string(),
  status: z.enum(['editorial', 'unassessed']),
  assessed_grade: z.enum(['A', 'B', 'C', 'D', 'E', 'F']).nullable(),
  basis: z.string(),
  scope: z.string(),
  limitations: z.array(z.string()),
  provenance_role: z.enum(['originator', 'publisher', 'aggregator', 'platform', 'unassessed']),
  publisher_reliability_assessed: z.boolean(),
  reviewed_at: z.string().nullable(),
}) satisfies z.ZodType<components['schemas']['SourceRatingOut']>;
export type SourceRating = z.infer<typeof sourceRatingSchema>;

export const CONNECTION_STATES = [
  'connected',
  'idle',
  'degraded',
  'failing',
  'key_missing',
  'key_unverified',
  'on_demand',
  'not_configured',
  'disabled_by_admin',
  'disabled_by_environment',
  'blocked_upstream',
  'available',
] as const;
export type ConnectionState = (typeof CONNECTION_STATES)[number];

const requirementSchema = z.object({
  kind: z.enum([
    'api_key',
    'credentials',
    'acknowledgement',
    'snapshot',
    'catalogue',
    'runtime',
    'model',
    'toggle',
    'endpoint',
  ]),
  satisfied: z.boolean().nullable(),
  origin: z.enum(['environment', 'database', 'none', 'unknown']),
  setting: z.string().max(200).nullable(),
  note: z.string().max(500),
  optional: z.boolean(),
}) satisfies z.ZodType<components['schemas']['SourceRequirementOut']>;
export type SourceRequirement = z.infer<typeof requirementSchema>;

const healthSummarySchema = z.object({
  status: z.enum(['idle', 'healthy', 'degraded', 'disabled']),
  last_success: z.string().nullable(),
  last_error_at: z.string().nullable(),
  consecutive_failures: z.number().int().nonnegative(),
  items_last_poll: z.number().int().nonnegative(),
  next_poll_at: z.string().nullable(),
  polls: z.number().int().nonnegative(),
  blocked_reason: z.string().max(300).nullable(),
}) satisfies z.ZodType<components['schemas']['SourceHealthSummaryOut']>;

export const sourceConnectionSchema = z.object({
  state: z.enum(CONNECTION_STATES),
  enabled: z.boolean(),
  environment_disabled: z.boolean(),
  active: z.boolean(),
  requirement: requirementSchema.nullable(),
  health: healthSummarySchema.nullable(),
  detail: z.string().max(500),
}) satisfies z.ZodType<components['schemas']['SourceConnectionOut']>;
export type SourceConnection = z.infer<typeof sourceConnectionSchema>;

export const sourceSummarySchema = z.object({
  id: z.string(),
  name: z.string(),
  organisation: z.string(),
  parent_organisation: z.string().nullable(),
  category: categorySchema,
  language: z.string(),
  reliability: z.enum(['A', 'B', 'C', 'D', 'E', 'F']),
  rating: sourceRatingSchema,
  coverage_scope: z.enum(['global', 'regional', 'unspecified']).default('unspecified'),
  coverage_countries: z.array(z.string()).default([]),
  coverage_regions: z.array(z.string()).default([]),
  coverage_note: z.string().default('Coverage has not been specified.'),
  kind: z.enum(['api', 'rss', 'geojson', 'websocket']).default('api'),
  requires_key: z.boolean().default(false),
  collection_mode: z.enum(['on_demand', 'scheduled']).default('scheduled'),
  connection: sourceConnectionSchema,
}) satisfies z.ZodType<components['schemas']['SourceSummaryOut']>;

export const ASSET_FAMILIES = [
  'camera_index',
  'map_layer',
  'ukraine_dataset',
  'reference_dataset',
] as const;
export type AssetFamily = (typeof ASSET_FAMILIES)[number];

// Homepages become link targets, so only absolute https addresses are accepted.
const homepageSchema = z
  .string()
  .max(500)
  .refine((value) => value.startsWith('https://'), 'Homepages must use https.');

export const sourceAssetSchema = z.object({
  id: z.string().max(120),
  name: z.string().max(200),
  family: z.enum(ASSET_FAMILIES),
  delivery: z.enum([
    'official_index',
    'curated_catalogue',
    'third_party_directory',
    'bundled_snapshot',
    'request_service',
    'browser_direct',
  ]),
  organisation: z.string().max(200),
  description: z.string().max(500),
  licence_note: z.string().max(1000),
  homepage: homepageSchema.nullable(),
  coverage_note: z.string().max(300),
  refresh_note: z.string().max(300),
  state: z.enum(CONNECTION_STATES),
  detail: z.string().max(500),
  requirement: requirementSchema.nullable(),
  as_of: z.string().max(40).nullable(),
  records: z.number().int().nonnegative().nullable(),
}) satisfies z.ZodType<components['schemas']['SourceAssetOut']>;
export type SourceAsset = z.infer<typeof sourceAssetSchema>;

export async function fetchSourceCatalogue() {
  return apiCall('/api/sources', {
    schema: z.object({
      items: z.array(sourceSummarySchema).max(2000),
      assets: z.array(sourceAssetSchema).max(1000).default([]),
    }),
  });
}

export type CatalogueSource = z.infer<typeof sourceSummarySchema>;

export const platformConnectionSchema = z.object({
  id: z.string().max(80),
  name: z.string().max(120),
  purpose: z.string().max(300),
  state: z.enum(CONNECTION_STATES),
  requirement: requirementSchema,
  detail: z.string().max(300),
}) satisfies z.ZodType<components['schemas']['PlatformConnectionOut']>;
export type PlatformConnection = z.infer<typeof platformConnectionSchema>;

export async function fetchPlatformConnections() {
  const response = await apiCall('/api/sources/connections', {
    schema: z.object({ items: z.array(platformConnectionSchema).max(50) }),
  });
  return response.items;
}
