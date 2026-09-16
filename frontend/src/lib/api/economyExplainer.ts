import { z } from 'zod';
import { apiCall } from './client';
import type { components } from './types.gen';

export type EconomyExplainer = components['schemas']['EconomyExplainerOut'];
export type ExplainerSection = components['schemas']['ExplainerSectionOut'];
export type ExplainerBody = components['schemas']['ExplainerBodyOut'];
export type ExplainerProvenance = components['schemas']['ExplainerProvenanceOut'];
export type ExplainerGlossaryEntry = components['schemas']['GlossaryEntryOut'];
export type ExplainerStatus = EconomyExplainer['status'];

const sectionSchema = z.object({
  takeaway: z.string(),
  paragraphs: z.array(z.string()).max(3),
  drivers: z.array(z.string()).max(4),
  watch: z.array(z.string()).max(4),
});
const explainerSchema: z.ZodType<EconomyExplainer> = z.object({
  status: z.enum(['ready', 'stale', 'generating', 'empty', 'unavailable', 'validation_failed']),
  stale: z.boolean(),
  reason: z.string().nullable(),
  explainer: z
    .object({
      world: sectionSchema,
      regions: z.array(z.object({ id: z.string(), section: sectionSchema })).max(5),
      glossary: z.array(z.object({ term: z.string(), plain_english: z.string() })).max(12),
    })
    .nullable(),
  provenance: z
    .object({
      model: z.string(),
      generated_at: z.iso.datetime({ offset: true }),
      snapshot_fetched_at: z.iso.datetime({ offset: true }),
      prompt_tokens: z.number().int().nullable(),
      completion_tokens: z.number().int().nullable(),
      sources: z.array(z.string()).max(6),
      written_by: z.string(),
    })
    .nullable(),
});

export const fetchEconomyExplainer = () =>
  apiCall('/api/economy/explainer', { schema: explainerSchema });

/** Administrators only: forces one regeneration, ignoring the daily cadence. */
export const refreshEconomyExplainer = () =>
  apiCall('/api/economy/explainer/refresh', {
    method: 'POST',
    schema: explainerSchema,
    retryAfterRefresh: false,
  });
