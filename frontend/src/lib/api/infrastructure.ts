import { z } from 'zod';
import { apiCall } from './client';
import type { components } from './types.gen';

export type Cable = components['schemas']['CableOut'];
export type NuclearFacility = components['schemas']['NuclearFacilityOut'];
export type GroundStation = components['schemas']['GroundStationOut'];
export type Infrastructure = components['schemas']['InfrastructureOut'];
const publicLink = z.url().refine((value) => {
  const url = new URL(value);
  return url.protocol === 'https:' && !url.username && !url.password && !url.port;
});
// Preserve historical dataset references. These links are never fetched by the app.
const historicalSourceLink = z.url().refine((value) => {
  const url = new URL(value);
  return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password && !url.port;
});
const longitude = z.number().min(-180).max(180);
const latitude = z.number().min(-90).max(90);
const text = z.string().max(2000);
export const infrastructureSchema = z.object({
  cables: z
    .array(
      z.object({
        id: text,
        name: text,
        category: text,
        path: z
          .array(z.tuple([longitude, latitude]))
          .min(2)
          .max(512),
        source_url: publicLink,
        note: text,
      }),
    )
    .max(3000),
  ground_stations: z
    .array(
      z.object({
        id: text,
        name: text,
        operator: text,
        country: z.string().length(2),
        longitude,
        latitude,
        source_url: publicLink,
        note: text,
      }),
    )
    .max(100),
  nuclear_facilities: z
    .array(
      z.object({
        id: text,
        name: text,
        country: text,
        country_code: z.string().regex(/^[A-Z]{3}$/),
        longitude,
        latitude,
        capacity_mw: z.number().min(0).max(100000).nullable(),
        capacity_year: z.number().int().min(1900).max(2099).nullable(),
        operator: text.nullable(),
        source_name: text,
        source_url: historicalSourceLink,
        geolocation_source: text,
        note: text,
      }),
    )
    .max(1000),
  nuclear_attribution: text,
  nuclear_licence_url: publicLink,
  nuclear_dataset_version: text,
  nuclear_snapshot_date: text,
  snapshot_date: text,
  cable_attribution: text,
  cable_licence_url: publicLink,
});
export function fetchInfrastructure(signal: AbortSignal): Promise<Infrastructure> {
  return apiCall('/api/map-infrastructure', { schema: infrastructureSchema, signal });
}
