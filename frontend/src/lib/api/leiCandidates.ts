import { z } from 'zod';
import { apiCall } from './client';
import type { components } from './types.gen';

export type LeiCandidate = components['schemas']['LeiCandidateOut'];
const schema = z.object({
  items: z
    .array(
      z.object({
        lei: z.string(),
        name: z.string(),
        jurisdiction: z.string(),
        status: z.string(),
      }),
    )
    .max(10),
}) satisfies z.ZodType<components['schemas']['LeiCandidatesOut']>;

export function findLeiCandidates(name: string, country: string, signal: AbortSignal) {
  return apiCall('/api/research/lei-candidates', {
    method: 'POST',
    body: { name, country: country || null },
    schema,
    signal,
    retryAfterRefresh: false,
  });
}
