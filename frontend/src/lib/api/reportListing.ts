import { z } from 'zod';

import { apiCall } from './client';
import { reportSummarySchema } from './reportSummary';
import type { components } from './types.gen';

export type ReportOrigin = components['schemas']['ReportOrigin'];
export type ReportPage = components['schemas']['ReportsOut'];
export const REPORT_PAGE_SIZE = 50;

const pageSchema = z.object({
  items: z.array(reportSummarySchema),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
  has_more: z.boolean(),
});

export function fetchReportPage(
  origin: ReportOrigin,
  offset: number,
  signal: AbortSignal,
): Promise<ReportPage> {
  const query = new URLSearchParams({
    origin,
    offset: String(offset),
    limit: String(REPORT_PAGE_SIZE),
  });
  return apiCall(`/api/reports?${query.toString()}`, { schema: pageSchema, signal });
}
