import { z } from 'zod';
import type { components } from './types.gen';

export const researchReceiptSchema = z.object({
  question: z.string(),
  mode: z.string(),
  focus: z.string(),
  languages: z.array(z.string()),
  terms: z.array(z.string()),
  since: z.string(),
  until: z.string(),
  collected_items: z.number().int(),
  policy_version: z.string(),
  attempts: z.array(
    z.object({
      source_id: z.string(),
      source_name: z.string(),
      status: z.enum([
        'completed',
        'empty',
        'unavailable',
        'unsupported',
        'failed',
        'timed_out',
        'budget_exhausted',
      ]),
      result_count: z.number().int(),
      explanation: z.string(),
      language: z.string().nullable(),
    }),
  ),
}) satisfies z.ZodType<components['schemas']['ResearchReceiptOut']>;
export type ResearchReceipt = z.infer<typeof researchReceiptSchema>;

const citationStatus = z.enum([
  'absent',
  'context_insufficient',
  'excerpt_present',
  'review_required',
]);
export const citationChecksSchema = z.object({
  method_version: z.string(),
  limitations: z.array(z.string()),
  judgements: z.array(
    z.object({
      judgement_id: z.string(),
      status: citationStatus,
      reasons: z.array(z.string()),
      citations: z.array(
        z.object({
          label: z.string(),
          relation: z.enum(['supporting', 'contradicting']),
          status: citationStatus,
          evidence_id: z.string().nullable(),
          source_content_hash: z.string().nullable(),
          excerpt: z
            .object({
              field: z.enum(['title', 'summary']),
              start: z.number().int(),
              end: z.number().int(),
              text: z.string(),
              sha256: z.string(),
            })
            .nullable(),
          reasons: z.array(z.string()),
          indicators: z.array(
            z.object({
              kind: z.enum([
                'name_mismatch',
                'date_mismatch',
                'number_mismatch',
                'negation_mismatch',
              ]),
              claim_values: z.array(z.string()),
              excerpt_values: z.array(z.string()),
              explanation: z.string(),
            }),
          ),
        }),
      ),
    }),
  ),
}) satisfies z.ZodType<components['schemas']['ReportCitationChecksOut']>;
export type CitationChecks = z.infer<typeof citationChecksSchema>;

export const evidenceAttributeSchema = z.object({
  key: z.string(),
  value: z.union([z.string(), z.number(), z.boolean(), z.null()]),
}) satisfies z.ZodType<components['schemas']['EvidenceAttributeOut']>;
