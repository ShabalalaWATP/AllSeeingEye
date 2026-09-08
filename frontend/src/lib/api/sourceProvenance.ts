import { z } from 'zod';
import type { components } from './types.gen';

export type TextTransformation = components['schemas']['TextTransformation'];
export type SourceDate = components['schemas']['SourceDate'];
export const textTransformationSchema = z.object({
  field: z.enum(['title', 'summary']),
  original_text: z.string(),
  transformed_text: z.string(),
  kind: z.enum(['translation', 'transliteration']),
  source_language: z.string(),
  target_language: z.string(),
  source_script: z.string().nullable().default(null),
  target_script: z.string().nullable().default(null),
  origin: z.enum(['operator', 'source', 'machine']),
  method: z.string(),
  model: z.string().nullable().default(null),
  profile_id: z.string().nullable().default(null),
  provider: z.string().nullable().default(null),
  actor_id: z.string().nullable().default(null),
  review_status: z.enum(['unreviewed', 'operator_declared']),
  limitations: z.array(z.string()).default([]),
}) satisfies z.ZodType<TextTransformation>;
export const sourceDateSchema = z.object({
  field: z.string(),
  raw_text: z.string(),
  role: z.enum(['publication', 'modification', 'occurrence', 'record_validity', 'unspecified']),
  calendar: z.enum(['gregorian', 'solar_hijri_icu33', 'unknown']),
  basis: z.enum(['operator', 'source_spec', 'source_metadata']),
  precision: z.enum(['instant', 'day', 'unknown']),
  status: z.enum(['resolved', 'ambiguous', 'unsupported', 'invalid']),
  value: z.string().nullable().default(null),
  day_start: z.string().nullable().default(null),
  day_end: z.string().nullable().default(null),
  method: z.string(),
  actor_id: z.string().nullable().default(null),
  limitations: z.array(z.string()).default([]),
}) satisfies z.ZodType<SourceDate>;

export const queryVariantSchema = z.object({
  language: z.string(),
  terms: z.array(z.string()),
  kind: z.enum(['translation', 'transliteration']).default('translation'),
  original_terms: z.array(z.string()).default([]),
  source_script: z.string().nullable().default(null),
  target_script: z.string().nullable().default(null),
  method: z.string().nullable().default(null),
}) satisfies z.ZodType<components['schemas']['QueryVariantIn']>;
