/** Frozen server assessments. These schemas validate policy output without recalculating it. */
import { z } from 'zod';
import type { components } from './types.gen';

export const contributionSchema = z.enum(['strong', 'moderate', 'limited', 'unassessed']);
const confidence = z.enum(['low', 'moderate', 'high']);
const strings = z.array(z.string());
const count = z.number().int().nonnegative();

export const evidenceAssessmentSchema = z.object({
  label: z.string(),
  event_id: z.string(),
  source_id: z.string(),
  reliability: z.string(),
  credibility: z.number().int(),
  contribution: contributionSchema,
  organisation: z.string().nullable(),
  flags: strings,
  reasons: strings,
});
export type EvidenceAssessment = z.infer<typeof evidenceAssessmentSchema>;

const contributionGroupSchema = z.object({
  id: z.string(),
  labels: strings,
  known_organisation: z.boolean(),
  contribution: contributionSchema,
  confirmed_strong: z.boolean(),
  corroborating_contribution: contributionSchema,
  possible_copy: z.boolean(),
});

export const judgementAssessmentSchema = z.object({
  judgement_id: z.string(),
  supporting_labels: strings,
  contradicting_labels: strings,
  invalid_labels: strings,
  support_groups: z.array(contributionGroupSchema),
  opposition_groups: z.array(contributionGroupSchema),
  support_tier: contributionSchema,
  opposition_tier: contributionSchema,
  balance: z.enum([
    'no_support',
    'support_only',
    'support_stronger',
    'opposition_at_least_as_strong',
  ]),
  status: z.enum(['supported', 'limited', 'contested', 'unsupported']),
  confidence_ceiling: confidence,
  final_confidence: confidence,
  explanation: strings,
  limitations: strings,
  improvements: strings,
});
export type JudgementAssessment = z.infer<typeof judgementAssessmentSchema>;

export const reportAssessmentSchema = z.object({
  method_version: z.string(),
  evidence: z.array(evidenceAssessmentSchema),
  judgements: z.array(judgementAssessmentSchema),
  tallies: z.object({
    evidence_items: count,
    declared_groups: count,
    unknown_provenance_items: count,
    possible_copy_groups: count,
    judgements: count,
    strong: count,
    moderate: count,
    limited: count,
    unassessed: count,
    supported_judgements: count,
    limited_judgements: count,
    contested_judgements: count,
    unsupported_judgements: count,
  }),
  validation_errors: count,
  validation_warnings: count,
  limitations: strings,
}) satisfies z.ZodType<components['schemas']['ReportAssessmentOut']>;
export type ReportAssessment = z.infer<typeof reportAssessmentSchema>;
