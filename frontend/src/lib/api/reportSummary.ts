import { z } from 'zod';

export const reportStatusSchema = z.enum(['ready', 'needs_review', 'failed']);
export type ReportStatus = z.infer<typeof reportStatusSchema>;

export const reportSummarySchema = z.object({
  team_id: z.uuid().nullable(),
  id: z.string(),
  template: z.string(),
  title: z.string(),
  scope: z.record(z.string(), z.unknown()),
  period_from: z.string(),
  period_to: z.string(),
  status: reportStatusSchema,
  created_by: z.string(),
  created_at: z.string(),
  latest_version: z.number().int(),
});
export type ReportSummary = z.infer<typeof reportSummarySchema>;
