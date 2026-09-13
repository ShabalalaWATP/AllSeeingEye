/** Reference notes keyed by a broadcast identifier: background, never confirmation of identity. */
import { z } from 'zod';

import { apiCall } from './client';
import type { components } from './types.gen';

export type ReferenceEntry = components['schemas']['ReferenceEntryOut'];
export type ReferenceLookup = components['schemas']['ReferenceLookupOut'];
export type ReferenceKind = ReferenceEntry['kind'];

const httpsLink = z.url().refine((value) => {
  const url = new URL(value);
  return url.protocol === 'https:' && !url.username && !url.password && !url.port;
});

export const referenceLookupSchema: z.ZodType<ReferenceLookup> = z.object({
  items: z
    .array(
      z.object({
        kind: z.enum(['vessel', 'aircraft', 'aircraft_type']),
        key: z.string().max(32),
        name: z.string().max(120),
        description: z.string().max(300),
        detail: z.string().max(200),
        links: z.array(z.object({ label: z.string().max(60), url: httpsLink })).max(4),
        provenance: z.string().max(200),
      }),
    )
    .max(50),
  retrieved_at: z.string(),
  caveat: z.string().max(400),
});

export function fetchReference(
  kind: ReferenceKind,
  keys: readonly string[],
  signal: AbortSignal,
): Promise<ReferenceLookup> {
  const query = new URLSearchParams({ kind, keys: keys.slice(0, 50).join(',') });
  return apiCall(`/api/reference?${query.toString()}`, { schema: referenceLookupSchema, signal });
}
