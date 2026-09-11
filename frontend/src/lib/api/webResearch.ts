import { z } from 'zod';
import type { components } from './types.gen';

const publicLink = z.url().refine((value) => {
  const url = new URL(value);
  return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password;
});

export const webResearchSchema = z.object({
  status: z.enum([
    'completed',
    'unavailable',
    'unsupported',
    'failed',
    'timed_out',
    'not_collected',
  ]),
  explanation: z.string(),
  retrieved_at: z.string(),
  requested_model: z.string().nullable(),
  returned_model: z.string().nullable(),
  profile_id: z.string().nullable(),
  profile_revision: z.number().int().nullable(),
  synthesis: z.string().max(12000), // Python counts code points, JS counts UTF-16 units.
  citations: z
    .array(
      z.object({
        url: publicLink,
        title: z.string(),
        start_index: z.number().int().min(0).max(6000),
        end_index: z.number().int().min(0).max(6000),
      }),
    )
    .max(12),
  consulted_urls: z.array(publicLink).max(20),
  tool_calls: z.number().int().min(0).max(3),
  request_count: z.number().int().min(0).max(1),
  prompt_tokens: z.number().int().nullable(),
  completion_tokens: z.number().int().nullable(),
  latency_ms: z.number(),
  policy_version: z.string(),
  notice: z.string(),
}) satisfies z.ZodType<components['schemas']['WebResearchOut']>;

export type WebResearch = components['schemas']['WebResearchOut'];
