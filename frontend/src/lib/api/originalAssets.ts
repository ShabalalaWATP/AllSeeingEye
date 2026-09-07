import { z } from 'zod';
import { apiBlob, apiCall, apiSend } from './client';
import type { components } from './types.gen';

export const originalAssetSchema = z.object({
  id: z.string(),
  report_id: z.string(),
  report_version_id: z.string(),
  version_number: z.number().int(),
  evidence_label: z.string(),
  source_id: z.string(),
  event_id: z.string(),
  sha256: z.string(),
  byte_count: z.number().int(),
  filename: z.string(),
  media_type: z.string(),
  permitted_use: z.string(),
  owner_id: z.string(),
  team_id: z.string().nullable(),
  uploader_id: z.string(),
  created_at: z.string(),
  expires_at: z.string(),
  reservation_expires_at: z.string(),
  status: z.enum(['reserved', 'uploading', 'active', 'deleted', 'expired']),
  transitioned_at: z.string().nullable(),
}) satisfies z.ZodType<components['schemas']['OriginalAssetOut']>;
export type OriginalAsset = z.infer<typeof originalAssetSchema>;
export type OriginalAssetReservation = components['schemas']['OriginalAssetReserveIn'];
const route = (reportId: string) => `/api/reports/${encodeURIComponent(reportId)}/original-assets`;
const assetRoute = (reportId: string, id: string) => `${route(reportId)}/${encodeURIComponent(id)}`;
export function listOriginalAssets(reportId: string, version: number, signal: AbortSignal) {
  return apiCall(`${route(reportId)}?version_number=${String(version)}`, {
    signal,
    schema: z.object({ items: z.array(originalAssetSchema) }),
  });
}
export function reserveOriginalAsset(
  reportId: string,
  body: OriginalAssetReservation,
  signal: AbortSignal,
) {
  return apiCall(route(reportId), { method: 'POST', body, signal, schema: originalAssetSchema });
}
export function uploadOriginalAsset(reportId: string, id: string, file: File, signal: AbortSignal) {
  return apiCall(`${assetRoute(reportId, id)}/content`, {
    method: 'PUT',
    rawBody: file,
    signal,
    schema: originalAssetSchema,
  });
}
export function downloadOriginalAsset(reportId: string, id: string, signal: AbortSignal) {
  return apiBlob(`${assetRoute(reportId, id)}/content`, { signal });
}
export function deleteOriginalAsset(reportId: string, id: string, signal: AbortSignal) {
  return apiSend(assetRoute(reportId, id), { method: 'DELETE', signal });
}
