/** Reports: generate from live evidence, list, read, export. */
import { z } from 'zod';

import { scopedMutation } from '@/lib/workspaceAccess';
import type { components } from './types.gen';

import { apiCall, apiFile, apiSend } from './client';
import type { DownloadedFile } from './client';
import { reportAssessmentSchema } from './reportAssessment';
import { claimLedgerSchema } from './claimLedger';
import { claimGenerationSchema } from './claimGeneration';
import {
  citationChecksSchema,
  evidenceAttributeSchema,
  researchReceiptSchema,
} from './reportResearch';
import { sourceRatingSchema } from './sourceContext';
import { researchContextSchema } from './researchContext';
import { reportChallengeSchema } from './reportChallenge';
import { evidenceGeometrySchema, observationSchema } from './observations';
import { projectSchema } from './projects';
import { sourceDateSchema, textTransformationSchema } from './sourceProvenance';

export const reportStatusSchema = z.enum(['ready', 'needs_review', 'failed']);
export type ReportStatus = z.infer<typeof reportStatusSchema>;

export const templateSchema = z.object({
  id: z.string(),
  title: z.string(),
  purpose: z.string(),
  needs_country: z.boolean(),
  needs_question: z.boolean(),
  needs_conflict: z.boolean(),
  needs_hazard: z.boolean(),
  window_hours: z.number().int(),
});
export type ReportTemplate = z.infer<typeof templateSchema>;

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
  transformations: z.array(textTransformationSchema).default([]),
  source_dates: z.array(sourceDateSchema).default([]),
  geometry: evidenceGeometrySchema.nullable().optional(),
  observation: observationSchema.nullable().optional(),
  project: projectSchema.nullable().optional(),
  source_rating: sourceRatingSchema.nullable().optional(),
  attributes: z.array(evidenceAttributeSchema).optional(),
  independence_key: z.string().optional(),
  captured_at: z.string().optional(),
  observed_at: z.string().nullable().optional(),
  content_hash: z.string().optional(),
  reliability: z.string().optional(),
  credibility: z.number().int().optional(),
  instrument: z.boolean().optional(),
  title_en: z.string().nullable().optional(),
  language: z.string().nullable().optional(),
  geo_confidence: z.string().nullable().optional(),
  story_id: z.string().nullable().optional(),
  lon: z.number().nullable().optional(),
  lat: z.number().nullable().optional(),
  label: z.string(),
  event_id: z.string(),
  source_id: z.string(),
  source_name: z.string(),
  category: z.string(),
  title: z.string(),
  summary: z.string().nullable(),
  url: z.string().nullable(),
  published_at: z.string().nullable(),
  grade: z.string(),
  grade_rationale: z.string(),
  country_iso: z.string().nullable(),
  flags: z.array(z.string()),
  archive_url: z.string().nullable(),
});
export type EvidenceItem = z.infer<typeof evidenceItemSchema>;

export const directionSchema = z.object({
  pir: z.string(),
  sirs: z.array(z.string()),
  eeis: z.array(z.string()),
  search_terms: z.array(z.string()),
  categories: z.array(z.string()),
});
export type Direction = z.infer<typeof directionSchema>;

export const advocacySchema = z.object({
  target: z.string(),
  argument: z.string(),
  evidence: labels,
  lower_confidence: z.boolean(),
  rationale: z.string(),
  confidence_before: z.string().nullable(),
  confidence_after: z.string().nullable(),
});
export type DevilsAdvocacy = z.infer<typeof advocacySchema>;

export const findingSchema = z.object({
  rule: z.string(),
  severity: z.enum(['error', 'warning']),
  location: z.string(),
  message: z.string(),
});
export type Finding = z.infer<typeof findingSchema>;

const documentInlineSchema = z.object({
  text: z.string().max(16_000),
  direction: z.enum(['auto', 'ltr', 'rtl']),
  citation_numbers: z.array(z.number().int().positive()).max(32),
});

const documentListItemSchema = z.object({
  text: z.string(),
  inlines: z.array(documentInlineSchema),
});

const documentTableCellSchema = z.object({
  text: z.string(),
  inlines: z.array(documentInlineSchema),
});

const documentTableSchema = z.object({
  title: z.string(),
  columns: z.array(z.string()).min(1).max(20),
  rows: z.array(z.array(documentTableCellSchema)).max(500),
  caption: z.string(),
});

const documentFigureSchema = z.object({
  title: z.string(),
  caption: z.string(),
  alt_text: z.string(),
  content_base64: z
    .string()
    .min(1)
    .max(13_400_000)
    .regex(/^[A-Za-z0-9+/]*={0,2}$/),
  media_type: z.enum(['image/png', 'image/jpeg']),
  width_px: z.number().int().min(1).max(10_000),
  height_px: z.number().int().min(1).max(10_000),
  citation_numbers: z.array(z.number().int().positive()).max(32),
});

const documentBlockSchema = z.object({
  kind: z.enum([
    'title',
    'heading',
    'annex',
    'subheading',
    'text',
    'warning',
    'metadata',
    'list',
    'table',
    'figure',
    'reference',
  ]),
  text: z.string(),
  inlines: z.array(documentInlineSchema),
  items: z.array(documentListItemSchema),
  ordered: z.boolean(),
  table: documentTableSchema.nullable(),
  figure: documentFigureSchema.nullable(),
});

export const reportPublicationSchema = z.object({
  schema_version: z.number().int().positive(),
  title: z.string(),
  reference: z.string(),
  language: z.string(),
  blocks: z.array(documentBlockSchema).max(2_000),
  references: z
    .array(
      z.object({
        number: z.number().int().positive(),
        evidence_label: z.string(),
        title: z.string(),
        original_title: z.string().nullable(),
        publisher: z.string(),
        language: z.string().nullable(),
        published_at: z.string().nullable(),
        accessed_at: z.string(),
        url: z.string().nullable(),
        archive_url: z.string().nullable(),
      }),
    )
    .max(500),
});
export type ReportPublication = z.infer<typeof reportPublicationSchema>;

export const reportVersionSchema = z.object({
  publication: reportPublicationSchema.nullable().optional(),
  claim_ledger: claimLedgerSchema.nullable().optional(),
  claim_generation: claimGenerationSchema.nullable().optional(),
  research_context: researchContextSchema.nullable().optional(),
  challenge: reportChallengeSchema.nullable().optional(),
  research: researchReceiptSchema.nullable().optional(),
  citation_checks: citationChecksSchema.nullable().optional(),
  assessment: reportAssessmentSchema.nullable().optional(),
  period_from: z.string().nullable().optional(),
  period_to: z.string().nullable().optional(),
  data_cutoff: z.string().nullable().optional(),
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
  direction: directionSchema.nullable(),
  devils_advocacy: advocacySchema.nullable(),
});
export type ReportVersion = z.infer<typeof reportVersionSchema>;

export const reportSchema = z.object({ report: reportSummarySchema, version: reportVersionSchema });
export type Report = z.infer<typeof reportSchema>;

export type ReportRequest = components['schemas']['ReportCreateIn'];

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

export function generateReport(
  request: ReportRequest,
  options: { runId?: string; signal?: AbortSignal } = {},
): Promise<Report> {
  return scopedMutation(() =>
    apiCall('/api/reports', {
      method: 'POST',
      body: request,
      schema: reportSchema,
      ...(options.runId ? { headers: { 'X-Research-Run-ID': options.runId } } : {}),
      ...(options.signal ? { signal: options.signal } : {}),
    }),
  );
}

export function fetchReport(id: string, version?: number, signal?: AbortSignal): Promise<Report> {
  const suffix = version === undefined ? '' : `?version=${String(version)}`;
  return apiCall(`/api/reports/${encodeURIComponent(id)}${suffix}`, {
    schema: reportSchema,
    ...(signal ? { signal } : {}),
  });
}

export function regenerateReport(id: string): Promise<Report> {
  return scopedMutation(() =>
    apiCall(`/api/reports/${encodeURIComponent(id)}/versions`, {
      method: 'POST',
      schema: reportSchema,
    }),
  );
}

export function fetchReportMarkdown(id: string, version?: number): Promise<DownloadedFile> {
  const suffix = version === undefined ? '' : `?version=${String(version)}`;
  return apiFile(`/api/reports/${encodeURIComponent(id)}/markdown${suffix}`, {
    headers: { Accept: 'application/zip, text/markdown;q=0.9' },
  });
}

export function deleteReport(id: string): Promise<void> {
  return scopedMutation(() =>
    apiSend(`/api/reports/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  );
}
