import { z } from 'zod';
import { apiCall } from './client';
import type { components } from './types.gen';

export type Cable = components['schemas']['CableOut'];
export type NuclearFacility = components['schemas']['NuclearFacilityOut'];
export type GroundStation = components['schemas']['GroundStationOut'];
export type DataCentre = components['schemas']['DataCentreOut'];
export type Site = components['schemas']['SiteOut'];
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
const optionalText = text.nullable().default(null);
const optionalLink = publicLink.nullable().default(null);
const links = z
  .array(z.object({ label: z.string().max(80), url: publicLink }))
  .max(6)
  .default([]);
const precision = z.enum(['site', 'mapped', 'city']);
const siteSchema = z.object({
  id: text,
  kind: z.string().max(40),
  name: text,
  operator: text,
  owner: optionalText,
  country: z.string().length(2).nullable().default(null),
  longitude,
  latitude,
  precision,
  description: optionalText,
  significance: optionalText,
  detail: optionalText,
  website: optionalLink,
  wikipedia: optionalLink,
  links,
  source_url: publicLink,
  note: text,
});
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
        operator: optionalText,
        owner: optionalText,
        description: optionalText,
        website: optionalLink,
        wikipedia: optionalLink,
        inception: optionalText,
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
        website: publicLink.nullable().default(null),
        wikipedia: publicLink.nullable().default(null),
        owner: optionalText,
        description: optionalText,
        wikidata: z.string().max(20).nullable().default(null),
        role: optionalText,
        significance: optionalText,
        detail: optionalText,
        precision: precision.nullable().default(null),
        links,
      }),
    )
    .max(500),
  data_centres: z
    .array(
      z.object({
        id: text,
        name: text,
        operator: text,
        owner: optionalText,
        country: z.string().length(2).nullable().default(null),
        city: optionalText,
        longitude,
        latitude,
        precision: precision.default('mapped'),
        description: optionalText,
        significance: optionalText,
        detail: optionalText,
        website: publicLink.nullable().default(null),
        wikipedia: optionalLink,
        links,
        source_url: publicLink,
        note: text,
      }),
    )
    .max(4000)
    .default([]),
  data_centre_attribution: text.default(''),
  data_centre_licence_url: publicLink.default('https://www.openstreetmap.org/copyright'),
  data_centre_snapshot_date: text.default(''),
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
        owner: optionalText,
        description: optionalText,
        website: optionalLink,
        wikipedia: optionalLink,
        wikidata: z.string().max(20).nullable().default(null),
      }),
    )
    .max(1000),
  energy_sites: z.array(siteSchema).max(3200).default([]),
  semiconductor_sites: z.array(siteSchema).max(300).default([]),
  site_attribution: text.default(''),
  site_licence_url: publicLink.default('https://www.openstreetmap.org/copyright'),
  site_snapshot_date: text.default(''),
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
