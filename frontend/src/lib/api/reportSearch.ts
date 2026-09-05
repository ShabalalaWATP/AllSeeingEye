/** Semantic search of saved report versions through a configured embeddings profile. */
import { z } from 'zod';

import { apiCall } from './client';
import { reportSummarySchema } from './reports';
import type { components } from './types.gen';

export type ReportSearchStatus = components['schemas']['ReportSearchStatusOut'];
export type ReportSearchResult = components['schemas']['ReportSearchOut'];
type ReportSearchRequest = components['schemas']['ReportSearchIn'];

const statusSchema = z.object({
  available: z.boolean(),
  indexed: z.number().int().nonnegative(),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  batch_size: z.number().int().positive(),
});

const resultSchema = z.object({
  items: z.array(z.object({ report: reportSummarySchema, score: z.number().min(-1).max(1) })),
  indexed: z.number().int().nonnegative(),
  total: z.number().int().nonnegative(),
});

export function fetchReportSearchStatus(): Promise<ReportSearchStatus> {
  return apiCall('/api/report-search', { schema: statusSchema });
}

export function indexSavedReports(): Promise<ReportSearchStatus> {
  return apiCall('/api/report-search/index', { method: 'POST', schema: statusSchema });
}

export function searchSavedReports(request: ReportSearchRequest): Promise<ReportSearchResult> {
  return apiCall('/api/report-search/query', {
    method: 'POST',
    body: request,
    schema: resultSchema,
  });
}
