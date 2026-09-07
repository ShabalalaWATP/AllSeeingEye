import { z } from 'zod';
import { claimRevisionSchema } from './claims';
import type { components } from './types.gen';

export type ClaimGenerationReceipt = components['schemas']['ClaimGenerationReceipt'];
export const claimGenerationSchema = z.object({
  schema_version: z.literal(1),
  status: z.enum([
    'completed',
    'empty',
    'invalid',
    'unavailable',
    'unsupported',
    'no_model',
    'rate_limited',
    'quota_exceeded',
  ]),
  revision_ids: z.array(z.string()).max(20),
  model_origin: claimRevisionSchema.shape.model_origin,
}) satisfies z.ZodType<ClaimGenerationReceipt>;
