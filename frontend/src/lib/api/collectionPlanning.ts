import { z } from 'zod';
import type { components } from './types.gen';
import { registryIdentifierSchema } from './registryRouting';
const candidate = z.object({
  id: z.string().min(1).max(64),
  label: z.string().min(1).max(200),
  identifiers: z.array(z.string().max(300)).max(8),
  registry_identifiers: z.array(registryIdentifierSchema).max(8).default([]),
  origin: z.literal('model'),
});
const task = z.object({
  id: z.string().min(1).max(64),
  source_id: z.string().max(120),
  purpose: z.enum(['challenge', 'disambiguation']),
  terms: z.array(z.string().min(1).max(300)).max(12),
  candidate_id: z.string().nullable().default(null),
  route: z.enum(['terms', 'candidate_identifier']).default('terms'),
  identifier_id: z.string().nullable().default(null),
  origin: z.literal('model'),
});
/** Frozen model proposals are output metadata, never trusted research request inputs. */
export const collectionPlanningSchema = z.object({
  policy_version: z.literal('ase-model-plan-v1'),
  status: z.enum(['applied', 'empty', 'rejected', 'unavailable', 'skipped']),
  requested_model: z.string().max(2048),
  returned_model: z.string().max(2048),
  call_count: z.number().int().min(0).max(1),
  reason: z.string().max(500),
  proposed_candidates: z.array(candidate).max(8),
  proposed_tasks: z.array(task).max(8),
  accepted_candidate_ids: z.array(z.string().max(64)).max(8),
  accepted_task_ids: z.array(z.string().max(128)).max(8),
});
export type CollectionPlanningTrace = components['schemas']['PlanningTraceOut'];
