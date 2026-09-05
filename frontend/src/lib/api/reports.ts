/** Reports: generate from live evidence, list, read, export. */
import { z } from 'zod';

import { categorySchema } from './eventSchemas';
import { apiCall, apiSend } from './client';

export const reportStatusSchema = z.enum(['ready', 'needs_review', 'failed']);
export type ReportStatus = z.infer<typeof reportStatusSchema>;

export const templateSchema = z.object({
  id: z.string(),
  title: z.string(),
  purpose: z.string(),
  needs_country: z.boolean(),
  needs_question: z.boolean(),
  window_hours: z.number().int(),
});
export type ReportTemplate = z.infer<typeof templateSchema>;

export const reportSummarySchema = z.object({
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

const labels = z.array(z.string());

export const keyJudgementSchema = z.object({
  id: z.string(),
  statement: z.string(),
  probability: z.string(),
  confidence: z.string(),
  confidence_statement: z.string(),
  supporting_evidence: labels,
  contradicting_evidence: labels,
  assumptions: labels,
  change_from_previous: z.string().nullable(),
  indicators: z.array(z.string()),
});

export const reportBodySchema = z.object({
  key_judgements: z.array(keyJudgementSchema),
  reporting: z.array(
    z.object({
      theme: z.string(),
      items: z.array(z.object({ text: z.string(), evidence: labels, grade: z.string() })),
    }),
  ),
  assessment: z.array(z.object({ heading: z.string(), text: z.string(), evidence: labels })),
  assumptions: z.array(z.object({ id: z.string(), text: z.string(), lynchpin: z.boolean() })),
  alternative_hypotheses: z.array(
    z.object({ text: z.string(), why_less_likely: z.string(), evidence: labels }),
  ),
  indicators_and_warning: z.object({ watch_condition: z.string(), changes: z.array(z.string()) }),
  gaps: z.array(z.object({ text: z.string(), eei: z.string().nullable() })),
  collection_recommendations: z.array(z.string()),
  sourcing_statement: z.string(),
});
export type ReportBody = z.infer<typeof reportBodySchema>;

export const evidenceItemSchema = z.object({
  label: z.string(),
  event_id: z.string(),
  source_id: z.string(),
  source_name: z.string(),
  category: z.string(),
  title: z.string(),
  summary: z.string().nullable(),
  url: z.string().nullable(),
  published_at: z.string(),
  grade: z.string(),
  grade_rationale: z.string(),
  country_iso: z.string().nullable(),
  flags: z.array(z.string()),
});
export type EvidenceItem = z.infer<typeof evidenceItemSchema>;

export const findingSchema = z.object({
  rule: z.string(),
  severity: z.enum(['error', 'warning']),
  location: z.string(),
  message: z.string(),
});
export type Finding = z.infer<typeof findingSchema>;

export const reportVersionSchema = z.object({
  number: z.number().int(),
  status: reportStatusSchema,
  body: reportBodySchema,
  findings: z.array(findingSchema),
  evidence: z.array(evidenceItemSchema),
  quality: z.record(z.string(), z.unknown()),
  markdown: z.string(),
  model: z.string(),
  prompt_tokens: z.number().int().nullable(),
  completion_tokens: z.number().int().nullable(),
  latency_ms: z.number(),
  attempts: z.number().int(),
  created_at: z.string(),
});
export type ReportVersion = z.infer<typeof reportVersionSchema>;

export const reportSchema = z.object({ report: reportSummarySchema, version: reportVersionSchema });
export type Report = z.infer<typeof reportSchema>;

export interface ReportRequest {
  template: string;
  country?: string;
  categories?: z.infer<typeof categorySchema>[];
  question?: string;
  window_hours?: number;
}

export async function fetchTemplates(): Promise<ReportTemplate[]> {
  const page = await apiCall('/api/reports/templates', {
    schema: z.object({ items: z.array(templateSchema) }),
  });
  return page.items;
}

export async function fetchReports(): Promise<ReportSummary[]> {
  const page = await apiCall('/api/reports', {
    schema: z.object({ items: z.array(reportSummarySchema) }),
  });
  return page.items;
}

export function generateReport(request: ReportRequest): Promise<Report> {
  return apiCall('/api/reports', { method: 'POST', body: request, schema: reportSchema });
}

export function fetchReport(id: string): Promise<Report> {
  return apiCall(`/api/reports/${encodeURIComponent(id)}`, { schema: reportSchema });
}

export function deleteReport(id: string): Promise<void> {
  return apiSend(`/api/reports/${encodeURIComponent(id)}`, { method: 'DELETE' });
}

export function markdownUrl(id: string): string {
  return `/api/reports/${encodeURIComponent(id)}/markdown`;
}
