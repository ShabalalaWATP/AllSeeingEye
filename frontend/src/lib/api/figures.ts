/** Public figures: a packaged office-holder roster placed by public reporting, never by tracking. */
import { z } from 'zod';

import { apiCall } from './client';
import { liveEventSchema } from './eventSchemas';
import type { components } from './types.gen';

export type PublicFigure = components['schemas']['FigureOut'];
export type FigureBoard = components['schemas']['FigureBoardOut'];
export type PlacementBasis = PublicFigure['placement']['basis'];

const text = z.string().max(2000);
const commonsLink = z.url().refine((value) => {
  const url = new URL(value);
  return (
    url.protocol === 'https:' &&
    url.hostname === 'commons.wikimedia.org' &&
    !url.username &&
    !url.password &&
    !url.port
  );
});

export const figureSchema: z.ZodType<PublicFigure> = z.object({
  id: z.string().min(1).max(40),
  wikidata_id: z.string().regex(/^Q\d{1,12}$/),
  name: z.string().min(1).max(120),
  office: z.string().min(1).max(120),
  role: z.enum([
    'head_of_state',
    'head_of_government',
    'head_of_state_and_government',
    'senior_official',
    'organisation',
  ]),
  country_iso: z.string().length(2).nullable(),
  organisation: z.string().max(80).nullable(),
  seat_name: z.string().max(120),
  portrait: z
    .object({
      png_base64: z
        .string()
        .regex(/^[A-Za-z0-9+/]+=*$/)
        .max(24000),
      licence: z.string().max(80),
      credit: z.string().max(300),
      source_url: commonsLink,
    })
    .nullable(),
  placement: z.object({
    latitude: z.number().min(-90).max(90),
    longitude: z.number().min(-180).max(180),
    basis: z.enum(['reported_place', 'reported_country', 'seat']),
    detail: text,
    event_id: z.string().max(200).nullable(),
    published_at: z.string().nullable(),
  }),
  mentions: z.number().int().nonnegative(),
  latest: z.array(liveEventSchema).max(5),
});

export const figureBoardSchema: z.ZodType<FigureBoard> = z.object({
  figures: z.array(figureSchema).max(120),
  window_hours: z.number().int().positive(),
  events_scanned: z.number().int().nonnegative(),
  roster_retrieved_at: z.string(),
  source_note: text,
  generated_at: z.string(),
  caveat: text,
});

export function fetchFigures(signal?: AbortSignal): Promise<FigureBoard> {
  return apiCall(
    '/api/figures',
    signal ? { schema: figureBoardSchema, signal } : { schema: figureBoardSchema },
  );
}

/** Validated base64 from the API is the only source of a portrait; nothing else is rendered. */
export function portraitUrl(figure: Pick<PublicFigure, 'portrait'>): string | null {
  return figure.portrait ? `data:image/png;base64,${figure.portrait.png_base64}` : null;
}

export const BASIS_LABELS: Record<PlacementBasis, string> = {
  reported_place: 'Reported location',
  reported_country: 'Reported country',
  seat: 'Seat of office',
};

export const ROLE_LABELS: Record<PublicFigure['role'], string> = {
  head_of_state: 'Head of state',
  head_of_government: 'Head of government',
  head_of_state_and_government: 'Head of state and government',
  senior_official: 'Senior official',
  organisation: 'Organisation leader',
};
