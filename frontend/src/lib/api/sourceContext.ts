import { z } from 'zod';

import { apiCall } from './client';
import { categorySchema } from './eventSchemas';
import type { components } from './types.gen';

export const sourceRatingSchema = z.object({
  policy_version: z.string(),
  status: z.enum(['editorial', 'unassessed']),
  assessed_grade: z.enum(['A', 'B', 'C', 'D', 'E', 'F']).nullable(),
  basis: z.string(),
  scope: z.string(),
  limitations: z.array(z.string()),
  provenance_role: z.enum(['originator', 'publisher', 'aggregator', 'platform', 'unassessed']),
  publisher_reliability_assessed: z.boolean(),
  reviewed_at: z.string().nullable(),
}) satisfies z.ZodType<components['schemas']['SourceRatingOut']>;
export type SourceRating = z.infer<typeof sourceRatingSchema>;

export const sourceSummarySchema = z.object({
  id: z.string(),
  name: z.string(),
  organisation: z.string(),
  parent_organisation: z.string().nullable(),
  category: categorySchema,
  language: z.string(),
  reliability: z.enum(['A', 'B', 'C', 'D', 'E', 'F']),
  rating: sourceRatingSchema,
}) satisfies z.ZodType<components['schemas']['SourceSummaryOut']>;

export async function fetchSourceCatalogue() {
  const response = await apiCall('/api/sources', {
    schema: z.object({ items: z.array(sourceSummarySchema) }),
  });
  return response.items;
}
