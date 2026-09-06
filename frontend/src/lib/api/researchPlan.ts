import { z } from 'zod';

import { apiCall } from './client';
import type { components } from './types.gen';

export type ResearchPlanInput = components['schemas']['ResearchPlanIn'];
export type ResearchPlan = components['schemas']['ResearchPlanOut'];
export type QueryVariant = components['schemas']['QueryVariantIn'];
export const planSchema: z.ZodType<ResearchPlan> = z.object({
  question: z.string(),
  since: z.string(),
  until: z.string(),
  languages: z.array(z.string()),
  mode: z.enum(['quick', 'detailed']),
  focus: z.enum(['general', 'company', 'domain', 'document', 'media']),
  subject: z.string().nullable(),
  country_iso: z.string().nullable(),
  tasks: z.array(
    z.object({
      source_id: z.string(),
      source_name: z.string(),
      selected: z.boolean(),
      supported: z.boolean(),
      language: z.string().nullable(),
      terms: z.array(z.string()),
      provenance: z.string(),
      temporal_scope: z.string(),
    }),
  ),
  request_limit: z.number(),
  seconds_limit: z.number(),
  item_limit: z.number(),
  policy_version: z.string(),
  model_calls: z.number(),
  translation_calls: z.number(),
  replans: z.number(),
});
export function previewResearchPlan(body: ResearchPlanInput, signal: AbortSignal) {
  return apiCall('/api/research/runs/plan', { method: 'POST', body, schema: planSchema, signal });
}
