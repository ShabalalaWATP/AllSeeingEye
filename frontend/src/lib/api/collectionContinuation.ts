import { z } from 'zod';
import type { components } from './types.gen';

const decision = z.enum(['continue', 'replan', 'sufficient']);
export const collectionContinuationSchema = z.object({
  policy_version: z.literal('ase-collection-review-v1'),
  decision,
  requested_decision: decision.nullable().default(null),
  basis: z.enum([
    'empty_results',
    'potential_conflict',
    'question_addressed',
    'insufficient_context',
    'invalid_or_unavailable',
  ]),
  rationale: z.string().max(1000),
  citations: z
    .array(
      z.object({
        event_id: z.string(),
        source_id: z.string(),
        content_hash: z.string(),
        field: z.enum(['title', 'summary']),
        quote: z.string().min(1).max(500),
      }),
    )
    .max(8),
  gaps: z.array(z.string()).max(8),
  model: z.string(),
  context_count: z.number().int().min(0).max(20),
  total_count: z.number().int().min(0).max(1000),
  override_reason: z.string().nullable().default(null),
});
export type CollectionContinuation = components['schemas']['ContinuationTraceOut'];
