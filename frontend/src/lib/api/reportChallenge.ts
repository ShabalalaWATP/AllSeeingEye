import { z } from 'zod';
import type { components } from './types.gen';
import { researchReceiptSchema } from './reportResearch';

export const reportChallengeSchema = z.object({
  method_version: z.string(),
  redrafted: z.boolean(),
  request_limit: z.number().int(),
  seconds_limit: z.number(),
  limitations: z.array(z.string()),
  searches: z.array(
    z.object({
      judgement_id: z.string(),
      statement: z.string(),
      terms: z.array(z.string()),
      status: z.enum(['attempted', 'unavailable', 'plan_missing', 'budget_exhausted']),
      attempts: researchReceiptSchema.shape.attempts,
      collected_items: z.number().int(),
      selected_event_ids: z.array(z.string()),
      explanation: z.string(),
    }),
  ),
  reviews: z.array(
    z.object({
      judgement_id: z.string(),
      statement: z.string(),
      status: z.enum(['completed', 'unavailable', 'invalid']),
      explanation: z.string(),
      advocacy: z
        .object({
          target: z.string(),
          argument: z.string(),
          evidence: z.array(z.string()),
          lower_confidence: z.boolean(),
          rationale: z.string(),
          confidence_before: z.enum(['low', 'moderate', 'high']).nullable(),
          confidence_after: z.enum(['low', 'moderate', 'high']).nullable(),
        })
        .nullable(),
    }),
  ),
}) satisfies z.ZodType<components['schemas']['ReportChallengeOut']>;
export type ReportChallenge = z.infer<typeof reportChallengeSchema>;
