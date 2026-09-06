import { z } from 'zod';

import { apiCall } from './client';
import { contributionSchema } from './reportAssessment';
import type { components } from './types.gen';

export const reportMethodologySchema = z.object({
  method_version: z.string(),
  title: z.string(),
  contribution_matrix: z.array(
    z.object({
      reliability: z.string(),
      credibility: z.number().int(),
      contribution: contributionSchema,
    }),
  ),
  reliability_scale: z.array(z.object({ grade: z.string(), label: z.string() })),
  credibility_scale: z.array(z.object({ grade: z.number().int(), label: z.string() })),
  assessment_dimensions: z.array(
    z.object({
      name: z.string(),
      engine_assessed: z.boolean(),
      description: z.string(),
    }),
  ),
  confidence_rules: z.array(z.string()),
  limitations: z.array(z.string()),
  doctrine_references: z.array(z.object({ title: z.string(), url: z.string() })),
  probability_yardstick: z.array(
    z.object({
      probability: z.enum([
        'remote_chance',
        'highly_unlikely',
        'unlikely',
        'realistic_possibility',
        'likely',
        'highly_likely',
        'almost_certain',
      ]),
      term: z.string(),
      low_percent: z.number().int(),
      high_percent: z.number().int(),
      range_description: z.string(),
    }),
  ),
}) satisfies z.ZodType<components['schemas']['ReportMethodologyOut']>;
export type ReportMethodology = z.infer<typeof reportMethodologySchema>;

export function fetchReportMethodology(): Promise<ReportMethodology> {
  return apiCall('/api/report-methodology', { schema: reportMethodologySchema });
}
