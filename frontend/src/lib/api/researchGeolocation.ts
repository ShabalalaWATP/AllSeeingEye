/** Explicit image disclosure and bounded visual analysis of a private attachment. */
import { z } from 'zod';

import { scopedMutation } from '@/lib/workspaceAccess';

import { apiCall, apiSend } from './client';
import { isApiError } from './errors';
import { researchInputReceiptSchema } from './researchInputs';
import type { components } from './types.gen';

export type ResearchGeolocationRequest = components['schemas']['PhotoGeolocationIn'];
export type ResearchGeolocation = components['schemas']['PhotoGeolocationOut'];

const notes = z.array(z.string().min(1).max(500)).max(12);
const hash = z.string().regex(/^[a-f0-9]{64}$/);
export const researchGeolocationSchema: z.ZodType<ResearchGeolocation> = z
  .object({
    input: researchInputReceiptSchema,
    candidate_status: z.literal('unverified'),
    status: z.enum(['candidates', 'unknown']),
    summary: z.string().min(1).max(1200),
    visual_clues: notes,
    photos: z
      .array(
        z.object({
          photo_id: z.string().regex(/^photo-[1-6]$/),
          visual_clues: notes,
          limitations: notes,
        }),
      )
      .max(6)
      .default([]),
    cross_photo_analysis: z.string().min(1).max(2000).nullable().default(null),
    candidates: z
      .array(
        z.object({
          label: z.string().min(1).max(200),
          country_iso: z
            .string()
            .regex(/^[A-Z]{2}$/)
            .nullable(),
          precision: z.enum(['country', 'region', 'city', 'landmark']),
          supporting_clues: notes,
          contradictions: notes,
          coordinates: z
            .object({
              latitude: z.number().min(-90).max(90),
              longitude: z.number().min(-180).max(180),
              uncertainty_radius_km: z.number().min(0.1).max(20_000),
              basis: z.string().min(10).max(500),
            })
            .nullable(),
        }),
      )
      .max(3),
    verification_steps: notes,
    limitations: notes,
    sun_checks: z
      .array(
        z.object({
          candidate_label: z.string().min(1).max(200),
          photo_id: z.string().regex(/^photo-[1-6]$/),
          status: z.enum(['consistent', 'inconsistent', 'sun_below_horizon', 'no_coordinates']),
          captured_at: z.iso.datetime({ offset: true }),
          sun_elevation_deg: z.number().nullable(),
          sun_azimuth_deg: z.number().nullable(),
          expected_shadow_ratio: z.number().nullable(),
          observed_shadow_ratio: z.number(),
          note: z.string().min(1).max(600),
        }),
      )
      .max(18)
      .default([]),
    provenance: z.object({
      profile_id: z.uuid(),
      profile_revision: z.number().int().positive(),
      provider: z.enum(['openai_compatible', 'bedrock']),
      configured_model: z.string().max(2048),
      returned_model: z.string().max(2048),
      analysed_at: z.iso.datetime({ offset: true }),
      original_sha256: hash,
      image_sha256: hash,
      photos: z
        .array(
          z.object({
            photo_id: z.string().regex(/^photo-[1-6]$/),
            input_id: z.uuid(),
            original_sha256: hash,
            image_sha256: hash,
          }),
        )
        .max(6)
        .default([]),
    }),
  })
  .refine((value) => (value.status === 'candidates') === value.candidates.length > 0)
  .refine(
    (value) => new Set(value.photos.map((photo) => photo.photo_id)).size === value.photos.length,
  )
  .refine(
    (value) =>
      new Set(value.provenance.photos.map((photo) => photo.photo_id)).size ===
      value.provenance.photos.length,
  );

export function geolocateResearchInput(
  inputId: string,
  request: ResearchGeolocationRequest,
  signal: AbortSignal,
): Promise<ResearchGeolocation> {
  return scopedMutation(() =>
    apiCall(`/api/research/inputs/${encodeURIComponent(inputId)}/geolocation`, {
      method: 'POST',
      body: request,
      signal,
      schema: researchGeolocationSchema,
    }),
  );
}

/** Expired or already removed transient receipts are an idempotent cleanup outcome. */
export function discardResearchInput(inputId: string, signal: AbortSignal): Promise<void> {
  return scopedMutation(async () => {
    try {
      await apiSend(`/api/research/inputs/${encodeURIComponent(inputId)}`, {
        method: 'DELETE',
        signal,
      });
    } catch (error) {
      if (!isApiError(error) || error.status !== 404) throw error;
    }
  });
}
