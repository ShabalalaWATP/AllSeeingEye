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
export type UkraineReference = components['schemas']['UkraineReferenceOut'];
export type EquipmentEntry = components['schemas']['EquipmentOut'];
export type ForceNode = components['schemas']['ForceNodeOut'];
export type TimelinePhase = components['schemas']['TimelinePhaseOut'];
export type TimelineEvent = components['schemas']['TimelineEventOut'];
export type ReferenceImage = components['schemas']['ReferenceImageOut'];
export type Side = components['schemas']['Side'];
export type ConfirmedLosses = components['schemas']['ConfirmedLossesOut'];
export type CivilianHarm = components['schemas']['CivilianHarmOut'];
export type LensSeries = components['schemas']['LensSeriesOut'];

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

const sideEnum = z.enum(['ru', 'ua']);
const lossRowSchema = z.object({
  side: sideEnum,
  equipment_type: z.string().max(80),
  group: z.string().max(40),
  destroyed: z.number().int().nonnegative(),
  damaged: z.number().int().nonnegative(),
  abandoned: z.number().int().nonnegative(),
  captured: z.number().int().nonnegative(),
  total: z.number().int().nonnegative(),
});
const confirmedSchema = z.object({
  recorded_on: z.string(),
  retrieved_at: z.string(),
  attribution: z.string().max(300),
  licence: z.string().max(120),
  source_url: z.string().max(300),
  rows: z.array(lossRowSchema).max(120),
  days: z
    .array(z.object({ on: z.string(), side: sideEnum, total: z.number().int().nonnegative() }))
    .max(62),
});
const civilianHarmSchema = z.object({
  retrieved_at: z.string(),
  source_url: z.string().max(300),
  attribution: z.string().max(300),
  months: z
    .array(
      z.object({
        month: z.string(),
        title: z.string().max(160),
        url: z.string().max(600),
        published_on: z.string().nullable(),
        killed: z.number().int().nonnegative().nullable(),
        injured: z.number().int().nonnegative().nullable(),
      }),
    )
    .max(36),
  references: z
    .array(
      z.object({
        id: z.string().max(60),
        label: z.string().max(160),
        text: z.string().max(600),
        basis: z.string().max(20),
        url: z.string().max(600),
        as_of: z.string(),
      }),
    )
    .max(12),
});
const lensSeriesSchema = z.object({
  lens: lensSchema,
  days: z.array(z.string()).max(31),
  groups: z.record(z.string().max(20), z.array(z.number().int().nonnegative()).max(31)),
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
  confirmed: confirmedSchema.nullable(),
  civilian_harm: civilianHarmSchema.nullable(),
  lens_series: z.array(lensSeriesSchema).max(5),
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

const sideSchema = z.enum(['ru', 'ua']);
const linkSchema = z.object({ label: z.string().max(120), url: z.string().max(600) });
const imageIdSchema = z
  .string()
  .regex(/^[a-z0-9][a-z0-9-]{0,59}$/)
  .nullable();
const qidSchema = z
  .string()
  .regex(/^Q\d{1,12}$/)
  .nullable();

export const ukraineReferenceSchema: z.ZodType<UkraineReference> = z.object({
  retrieved_at: z.string(),
  source_note: z.string().max(400),
  specialities: z
    .array(
      z.object({
        key: z.string().max(40),
        label: z.string().max(80),
        subgroups: z.record(z.string().max(40), z.string().max(80)),
      }),
    )
    .max(20),
  themes: z.record(z.string().max(40), z.string().max(80)),
  equipment: z
    .array(
      z.object({
        id: z.string().max(60),
        side: sideSchema,
        group: z.string().max(40),
        subgroup: z.string().max(40),
        name: z.string().max(160),
        origin: z.string().max(80),
        role: z.string().max(160),
        description: z.string().max(900),
        numbers: z.string().max(400).nullable(),
        wikidata_id: qidSchema,
        image_id: imageIdSchema,
        as_of: z.string(),
        links: z.array(linkSchema).max(8),
      }),
    )
    .max(200),
  forces: z
    .array(
      z.object({
        id: z.string().max(60),
        side: sideSchema,
        parent_id: z.string().max(60).nullable(),
        name: z.string().max(160),
        role: z.string().max(900),
        commander: z.string().max(120).nullable(),
        figure_id: z.string().max(60).nullable(),
        strength: z.string().max(400).nullable(),
        wikidata_id: qidSchema,
        image_id: imageIdSchema,
        as_of: z.string(),
        links: z.array(linkSchema).max(8),
      }),
    )
    .max(160),
  phases: z
    .array(
      z.object({
        id: z.string().max(60),
        label: z.string().max(160),
        start: z.string(),
        end: z.string().nullable(),
        summary: z.string().max(900),
      }),
    )
    .max(16),
  events: z
    .array(
      z.object({
        id: z.string().max(60),
        phase_id: z.string().max(60),
        on: z.string(),
        title: z.string().max(160),
        text: z.string().max(900),
        theme: z.string().max(40),
        wikidata_id: qidSchema,
        image_id: imageIdSchema,
        links: z.array(linkSchema).max(8),
      }),
    )
    .max(160),
  images: z.record(
    z.string().max(60),
    z.object({
      id: z.string().max(60),
      licence: z.string().max(80),
      credit: z.string().max(300),
      source_url: z.string().max(600),
      width: z.number().int().nonnegative(),
      height: z.number().int().nonnegative(),
    }),
  ),
});

export function fetchUkraineReference(signal?: AbortSignal): Promise<UkraineReference> {
  return apiCall(
    '/api/conflicts/ukraine/reference',
    signal ? { schema: ukraineReferenceSchema, signal } : { schema: ukraineReferenceSchema },
  );
}

/** Same-origin path of a cached reference image; the id is validated by the schema. */
export function referenceImagePath(imageId: string): string {
  return `/api/conflicts/ukraine/images/${imageId}.jpg`;
}

export const SIDE_LABELS: Record<Side, string> = { ru: 'Russia', ua: 'Ukraine' };

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
