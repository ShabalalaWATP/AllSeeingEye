/** Binary exports and version comparisons through the authenticated API client. */
import { z } from 'zod';

import { apiBlob, apiCall } from './client';
import type { components } from './types.gen';

export type ReportComparison = components['schemas']['ReportComparisonOut'];
export type ReportChange = components['schemas']['ReportChangeOut'];
export type ReportExportFormat = components['schemas']['ExportFormat'];

const comparisonSchema: z.ZodType<ReportComparison> = z.object({
  from_version: z.number().int().positive(),
  to_version: z.number().int().positive(),
  changes: z.array(
    z.object({
      section: z.string(),
      path: z.string(),
      kind: z.enum(['added', 'removed', 'changed']),
      before: z.string().nullable(),
      after: z.string().nullable(),
    }),
  ),
});

export function fetchReportComparison(
  id: string,
  from: number,
  to: number,
  signal?: AbortSignal,
): Promise<ReportComparison> {
  return apiCall(
    `/api/reports/${encodeURIComponent(id)}/diff?from_version=${String(from)}&to_version=${String(to)}`,
    { schema: comparisonSchema, ...(signal ? { signal } : {}) },
  );
}

export function fetchReportFile(
  id: string,
  version: number,
  format: ReportExportFormat,
): Promise<Blob> {
  return apiBlob(
    `/api/reports/${encodeURIComponent(id)}/export/${format}?version=${String(version)}`,
  );
}

export function fetchEvidencePackage(id: string, version: number, signal: AbortSignal) {
  return apiBlob(
    `/api/reports/${encodeURIComponent(id)}/evidence-package?version=${String(version)}`,
    { signal },
  );
}
