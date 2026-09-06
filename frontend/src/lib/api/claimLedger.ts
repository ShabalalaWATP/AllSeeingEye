import { z } from 'zod';
import type { components } from './types.gen';
import { judgementAssessmentSchema } from './reportAssessment';
import { citationChecksSchema } from './reportResearch';

export const claimLedgerSchema = z.object({
  derivation_version: z.string(),
  report_version: z.number().int(),
  limitations: z.array(z.string()),
  recorded_gaps: z.array(z.string()),
  claims: z.array(
    z.object({
      id: z.string(),
      judgement_id: z.string(),
      statement: z.string(),
      kind: z.literal('analytical_inference'),
      confidence_statement: z.string(),
      assumptions: z.array(z.string()),
      assessment: judgementAssessmentSchema.nullable(),
      citation_checks: citationChecksSchema.shape.judgements.element.nullable(),
      sources: z.array(
        z.object({
          label: z.string(),
          relation: z.enum(['supporting', 'contradicting']),
          evidence_id: z.string().nullable(),
          source_name: z.string().nullable(),
          organisation: z.string().nullable(),
          content_hash: z.string().nullable(),
        }),
      ),
      dimensions: z.array(
        z.object({
          name: z.enum([
            'evidence_support',
            'source_independence',
            'coverage',
            'citation_validity',
          ]),
          status: z.string(),
          explanation: z.string(),
        }),
      ),
    }),
  ),
}) satisfies z.ZodType<components['schemas']['ClaimLedgerOut']>;

export type ClaimLedger = components['schemas']['ClaimLedgerOut'];
