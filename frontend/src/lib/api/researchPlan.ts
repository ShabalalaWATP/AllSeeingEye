import { z } from 'zod';

import { apiCall } from './client';
import type { components } from './types.gen';
import { collectionPlanningSchema } from './collectionPlanning';
import { collectionContinuationSchema } from './collectionContinuation';
import { registryIdentifierSchema, registryLookupSchema } from './registryRouting';

export type ResearchPlanInput = components['schemas']['ResearchPlanIn'];
export type ResearchPlan = components['schemas']['ResearchPlanOut'];
export type QueryVariant = components['schemas']['QueryVariantIn'];
export const candidateHypothesisSchema = z.object({
  id: z.string(),
  label: z.string(),
  identifiers: z.array(z.string()),
  registry_identifiers: z.array(registryIdentifierSchema).max(8).default([]),
});
export const plannedQueryTaskSchema = z.object({
  id: z.string(),
  source_id: z.string(),
  purpose: z.enum(['challenge', 'disambiguation']),
  terms: z.array(z.string()),
  candidate_id: z.string().nullable(),
  route: z.enum(['terms', 'candidate_identifier']).default('terms'),
  identifier_id: z.string().nullable().default(null),
});
export type CandidateHypothesis = components['schemas']['ResearchCandidateIn'];
export type PlannedQueryTask = components['schemas']['PlannedQueryTaskIn'];
const areaSchema = z.object({
  geometry: z.record(z.string(), z.unknown()),
  sha256: z.string().regex(/^[0-9a-f]{64}$/),
});
export const planSchema: z.ZodType<ResearchPlan> = z.object({
  question: z.string(),
  time_basis: z
    .enum(['publication', 'acquisition_or_publication', 'recorded_time'])
    .default('publication'),
  since: z.string(),
  until: z.string(),
  languages: z.array(z.string()),
  mode: z.enum(['quick', 'detailed']),
  focus: z.enum(['general', 'company', 'domain', 'document', 'media']),
  subject: z.string().nullable(),
  country_iso: z.string().nullable(),
  area: areaSchema.nullable().default(null),
  candidate_hypotheses: z
    .array(
      candidateHypothesisSchema.extend({
        origin: z.enum(['operator', 'model']).default('operator'),
      }),
    )
    .max(8)
    .default([]),
  planning: collectionPlanningSchema.nullable().default(null),
  continuation: collectionContinuationSchema.nullable().default(null),
  tasks: z.array(
    z.object({
      source_id: z.string(),
      task_id: z.string().nullable().default(null),
      purpose: z.enum(['baseline', 'challenge', 'disambiguation']).default('baseline'),
      candidate_id: z.string().nullable().default(null),
      planned_terms_supported: z.boolean().default(false),
      registry_lookup: registryLookupSchema.nullable().default(null),
      registry_namespaces: z.array(z.string()).default([]),
      registry_options: z.array(registryLookupSchema).default([]),
      source_name: z.string(),
      selected: z.boolean(),
      supported: z.boolean(),
      language: z.string().nullable(),
      query_language: z.string().nullable().default(null),
      terms: z.array(z.string()),
      provenance: z.string(),
      temporal_scope: z.string(),
      spatial_supported: z.boolean().default(false),
      spatial_scope: z.string().default('No area-based collection support.'),
    }),
  ),
  request_limit: z.number(),
  seconds_limit: z.number(),
  item_limit: z.number(),
  policy_version: z.string(),
  model_calls: z.number(),
  translation_calls: z.number(),
  replans: z.number(),
  translation: z
    .object({
      policy_version: z.string(),
      original_terms: z.array(z.string()),
      languages: z.array(z.string()),
      model: z.string(),
      status: z.enum(['completed', 'failed', 'unavailable']),
      variants: z.array(z.object({ language: z.string(), terms: z.array(z.string()) })),
    })
    .nullable()
    .default(null),
});
export const previewSchema: z.ZodType<components['schemas']['ResearchPreviewOut']> = planSchema.and(
  z.object({
    map_origin: z
      .object({
        view_id: z.uuid(),
        revision_id: z.uuid(),
        report_id: z.uuid(),
        report_version_id: z.uuid(),
        report_version_number: z.number().int().positive(),
        content_sha256: z.string().regex(/^[0-9a-f]{64}$/),
        evidence_sha256: z.string().regex(/^[0-9a-f]{64}$/),
        area: areaSchema,
      })
      .nullable()
      .default(null),
  }),
);
export function previewResearchPlan(body: ResearchPlanInput, signal: AbortSignal) {
  return apiCall('/api/research/runs/plan', {
    method: 'POST',
    body,
    schema: previewSchema,
    signal,
  });
}
