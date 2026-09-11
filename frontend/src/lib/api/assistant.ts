import { z } from 'zod';
import { apiCall } from './client';
import type { components } from './types.gen';

export type AssistantRequest = components['schemas']['AssistantAnswerIn'];
export type AssistantAnswer = components['schemas']['AssistantAnswerOut'];
export const assistantAnswerSchema: z.ZodType<AssistantAnswer> = z.object({
  paragraphs: z.array(
    z.object({
      kind: z.enum(['finding', 'inference', 'gap']),
      text: z.string(),
      citations: z.array(z.string()),
    }),
  ),
  sources: z.array(
    z.object({
      id: z.string(),
      kind: z.enum(['event', 'camera', 'infrastructure', 'gnss']),
      record_id: z.string(),
      source_id: z.string(),
      title: z.string(),
      url: z.string().nullable(),
      published_at: z.string().nullable(),
      observed_at: z.string().nullable(),
      point: z.object({ lon: z.number(), lat: z.number() }).nullable(),
      grade: z.string().nullable(),
    }),
  ),
  scope: z.object({
    mode: z.enum(['global', 'viewport', 'selected']),
    bbox: z
      .object({ west: z.number(), south: z.number(), east: z.number(), north: z.number() })
      .nullable(),
    selected: z
      .object({ kind: z.enum(['event', 'camera', 'infrastructure']), id: z.string() })
      .nullable(),
  }),
  coverage: z.object({
    candidate_count: z.number().int().nonnegative(),
    matched_count: z.number().int().nonnegative(),
    selected_count: z.number().int().nonnegative(),
    source_count: z.number().int().nonnegative(),
    capped: z.boolean(),
    notes: z.array(z.string()),
  }),
  generated_at: z.string(),
  model: z.object({ name: z.string(), reasoning_effort: z.string().nullable() }).nullable(),
});

export function askAssistant(body: AssistantRequest, signal: AbortSignal) {
  return apiCall('/api/assistant/answer', {
    method: 'POST',
    body,
    schema: assistantAnswerSchema,
    signal,
    retryAfterRefresh: false,
  });
}
