/** Ukraine war tracker: reported control, claimed figures and grouped updates, never verified facts. */
import { z } from 'zod';

import { apiCall } from './client';
import { liveEventSchema } from './eventSchemas';
import type { components } from './types.gen';

export type UkraineBoard = components['schemas']['UkraineBoardOut'];
export type UkraineUpdate = components['schemas']['UpdateOut'];
export type ClaimedLosses = components['schemas']['ClaimedLossesOut'];
export type ControlSummary = components['schemas']['ControlSummaryOut'];
export type UkraineControl = components['schemas']['ControlOut'];
export type Settlement = components['schemas']['SettlementOut'];
export type ControlStatus = components['schemas']['ControlStatus'];
export type UpdateGroup = components['schemas']['UpdateGroup'];
export type Lens = components['schemas']['Lens'];

const statusSchema = z.enum(['ua', 'ru', 'contested', 'unknown']);
const groupSchema = z.enum(['assessments', 'ukrainian', 'russian', 'international']);
const lensSchema = z.enum(['equipment', 'workforce', 'casualties', 'strikes', 'diplomacy']);
const counts = z.record(z.string().max(60), z.number().int().nonnegative());
const polygons = z.array(z.array(z.array(z.tuple([z.number(), z.number()])).max(5000)).max(50));

const claimSchema: z.ZodType<ClaimedLosses> = z.object({
  reported_on: z.string(),
  day: z.number().int().positive(),
  source_url: z.string().max(2000).nullable(),
  totals: counts,
  increase: counts,
});

const summarySchema: z.ZodType<ControlSummary> = z.object({
  assessment_date: z.string(),
  release_stamp: z.string().max(40),
  retrieved_at: z.string(),
  attribution: z.string().max(400),
  licence: z.string().max(40),
  source_url: z.string().max(200),
  method_note: z.string().max(600),
  places_total: z.number().int().nonnegative(),
  retained: z.number().int().nonnegative(),
  counts,
  oblasts: z
    .array(
      z.object({
        name: z.string().max(80),
        total: z.number().int().nonnegative(),
        ua: z.number().int().nonnegative(),
        ru: z.number().int().nonnegative(),
        contested: z.number().int().nonnegative(),
        unknown: z.number().int().nonnegative(),
      }),
    )
    .max(30),
  changes: z
    .array(
      z.object({
        geoname_id: z.number().int(),
        name: z.string().max(80),
        oblast: z.string().max(80),
        previous: statusSchema,
        status: statusSchema,
        changed_on: z.string(),
      }),
    )
    .max(300),
});

export const ukraineBoardSchema: z.ZodType<UkraineBoard> = z.object({
  generated_at: z.string(),
  day_number: z.number().int().positive(),
  day_basis: z.enum(['claimed', 'computed']),
  window_days: z.number().int().positive(),
  events_scanned: z.number().int().nonnegative(),
  updates: z
    .array(z.object({ event: liveEventSchema, group: groupSchema, lenses: z.array(lensSchema) }))
    .max(200),
  lens_counts: counts,
  claims: z.array(claimSchema).max(100),
  categories: z.record(z.string().max(60), z.string().max(80)),
  headline_categories: z.array(z.string().max(60)).max(20),
  control: summarySchema.nullable(),
  freshness: z.object({
    control_assessed: z.string().nullable(),
    assessment_published: z.string().nullable(),
    claim_reported: z.string().nullable(),
    latest_update: z.string().nullable(),
  }),
});

export const ukraineControlSchema: z.ZodType<UkraineControl> = z.object({
  summary: summarySchema.nullable(),
  settlements: z
    .array(
      z.object({
        geoname_id: z.number().int(),
        name: z.string().max(80),
        oblast: z.string().max(80),
        lat: z.number().min(-90).max(90),
        lon: z.number().min(-180).max(180),
        status: statusSchema,
        since: z.string().nullable(),
        votes: z.array(statusSchema).length(4),
      }),
    )
    .max(12000),
  areas: z.array(z.object({ status: statusSchema, polygons })).max(4),
  outlines: z
    .array(z.object({ name: z.string().max(80), iso: z.string().max(8), polygons }))
    .max(30),
});

export function fetchUkraineBoard(signal?: AbortSignal): Promise<UkraineBoard> {
  return apiCall(
    '/api/conflicts/ukraine',
    signal ? { schema: ukraineBoardSchema, signal } : { schema: ukraineBoardSchema },
  );
}

export function fetchUkraineControl(signal?: AbortSignal): Promise<UkraineControl> {
  return apiCall(
    '/api/conflicts/ukraine/control',
    signal ? { schema: ukraineControlSchema, signal } : { schema: ukraineControlSchema },
  );
}

export const GROUP_LABELS: Record<UpdateGroup, string> = {
  assessments: 'Assessments',
  ukrainian: 'Ukrainian reporting',
  russian: 'Russian and independent Russian',
  international: 'International',
};

export const LENS_LABELS: Record<Lens, string> = {
  equipment: 'Equipment',
  workforce: 'Workforce',
  casualties: 'Casualties',
  strikes: 'Strikes',
  diplomacy: 'Diplomacy',
};

export const STATUS_LABELS: Record<ControlStatus, string> = {
  ua: 'Ukrainian-held (reported)',
  ru: 'Russian-held (reported)',
  contested: 'Contested (reported)',
  unknown: 'No reported status',
};
