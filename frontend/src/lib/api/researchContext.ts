import { z } from 'zod';
import type { components } from './types.gen';
import { evidenceAttributeSchema } from './reportResearch';

const identityValue = z.object({ namespace: z.string(), value: z.string() });
export const researchContextSchema = z.object({
  method_version: z.string(),
  limitations: z.array(z.string()),
  timeline: z.array(
    z.object({
      evidence_label: z.string(),
      title: z.string(),
      published_at: z.string(),
      captured_at: z.string(),
      observed_at: z.string().nullable(),
      timestamp_basis: z.string().nullable(),
      date_precision: z.string().nullable(),
      current_snapshot: z.boolean().nullable(),
      record_kind: z.string().nullable(),
      temporal_attributes: z.array(evidenceAttributeSchema),
      limitations: z.array(z.string()),
    }),
  ),
  identity_candidates: z.array(
    z.object({
      evidence_label: z.string(),
      identifiers: z.array(identityValue),
      aliases: z.array(identityValue),
      declared_match_status: z.string().nullable(),
      status: z.literal('unverified_candidate'),
    }),
  ),
  source_chains: z.array(
    z.object({
      evidence_label: z.string(),
      collector_source_id: z.string(),
      relation: z.enum(['declared_publisher', 'declared_account', 'declared_source']),
      declared_name: z.string().nullable(),
      declared_id: z.string().nullable(),
      declared_url: z.string().nullable(),
      status: z.literal('unverified_attribution'),
    }),
  ),
  source_relationships: z.array(
    z.object({
      evidence_labels: z.tuple([z.string(), z.string()]),
      reasons: z.array(z.string()),
      shared_parent: z.string().nullable(),
      status: z.literal('unverified_relationship'),
    }),
  ),
}) satisfies z.ZodType<components['schemas']['ResearchContextOut']>;
export type ResearchContext = z.infer<typeof researchContextSchema>;
