/**
 * Fortnightly AI digest of the Ukraine page sources. The model writes it from evidence this
 * application already collected; nothing in it is verified, and every change names its evidence.
 */
import { z } from 'zod';

import { apiCall } from './client';
import type { components } from './types.gen';

export type UkraineDigestView = components['schemas']['UkraineDigestOut'];
export type UkraineDigestEntry = components['schemas']['DigestEntryOut'];
export type UkraineDigestStatus = components['schemas']['DigestStatus'];
export type UkraineDigestStrand = components['schemas']['DigestStrandOut'];
export type UkraineDigestChange = components['schemas']['DigestChangeOut'];
export type UkraineDigestCitation = components['schemas']['DigestCitationOut'];

const citationSchema: z.ZodType<UkraineDigestCitation> = z.object({
  id: z.string().max(8),
  kind: z.string().max(20),
  source_id: z.string().max(60),
  label: z.string().max(200),
  dated_on: z.string().nullable(),
  url: z.string().max(2000).nullable(),
});

const strandSchema: z.ZodType<UkraineDigestStrand> = z.object({
  summary: z.string().max(900),
  changes: z
    .array(z.object({ text: z.string().max(400), source_ids: z.array(z.string().max(8)).max(4) }))
    .max(5),
});

const entrySchema: z.ZodType<UkraineDigestEntry> = z.object({
  period_start: z.string(),
  period_end: z.string(),
  generated_at: z.string(),
  model: z.string().max(2048),
  evidence_items: z.number().int().nonnegative(),
  source_ids: z.array(z.string().max(60)).max(40),
  prompt_tokens: z.number().int().nonnegative().nullable(),
  completion_tokens: z.number().int().nonnegative().nullable(),
  battlefield: strandSchema,
  political: strandSchema,
  watch: z.array(z.string().max(260)).max(4),
  caveats: z.array(z.string().max(260)).max(3),
  citations: z.array(citationSchema).max(24),
});

export const ukraineDigestSchema: z.ZodType<UkraineDigestView> = z.object({
  status: z.enum(['ready', 'none', 'generating', 'unavailable', 'validation_failed']),
  reason: z.string().max(600).nullable(),
  stale: z.boolean(),
  generating: z.boolean(),
  interval_days: z.number().int().positive(),
  latest: entrySchema.nullable(),
  previous: z.array(entrySchema).max(8),
});

export function fetchUkraineDigest(signal?: AbortSignal): Promise<UkraineDigestView> {
  return apiCall(
    '/api/conflicts/ukraine/digest',
    signal ? { schema: ukraineDigestSchema, signal } : { schema: ukraineDigestSchema },
  );
}

/** Administrators only. One request asks for a new digest; the work runs in the background. */
export function refreshUkraineDigest(): Promise<UkraineDigestView> {
  return apiCall('/api/conflicts/ukraine/digest/refresh', {
    method: 'POST',
    schema: ukraineDigestSchema,
    // Costly work: refresh the session, but never resubmit the spend automatically.
    retryAfterRefresh: false,
  });
}
