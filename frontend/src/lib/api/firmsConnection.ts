import { z } from 'zod';
import type { components } from './types.gen';
import { apiCall } from './client';
import { scopedMutation } from '@/lib/workspaceAccess';

export type FirmsConnection = components['schemas']['FirmsConnectionOut'];
export type FirmsConnectionTest = components['schemas']['FirmsConnectionTestOut'];
export const FIRMS_ID = 'firms_viirs_noaa20';
const base = `/api/admin/sources/${FIRMS_ID}/connection`;
const revision = z.number().int().nonnegative();
export const firmsConnectionSchema = z.object({
  revision,
  active_revision: revision,
  configured: z.boolean(),
  credential_origin: z.enum(['environment', 'database', 'none']),
  environment_disabled: z.boolean(),
  encryption_available: z.boolean(),
  area: z.string(),
  draft_present: z.boolean(),
  draft_expires_at: z.iso.datetime({ offset: true }).nullable(),
  tested_at: z.iso.datetime({ offset: true }).nullable(),
  test_generation: revision,
  test_ok: z.boolean(),
}) satisfies z.ZodType<FirmsConnection>;
const testSchema = z.object({
  status: firmsConnectionSchema,
  ok: z.boolean(),
  fetched: revision,
  message: z.string(),
}) satisfies z.ZodType<FirmsConnectionTest>;
export function fetchFirmsConnection(signal: AbortSignal) {
  return apiCall(base, { signal, schema: firmsConnectionSchema });
}
export function saveFirmsDraft(
  body: components['schemas']['FirmsDraftIn'],
  signal: AbortSignal,
) {
  return scopedMutation(() =>
    apiCall(`${base}/draft`, { method: 'PUT', body, signal, schema: firmsConnectionSchema }),
  );
}
export function testFirmsDraft(expectedRevision: number, signal: AbortSignal) {
  return scopedMutation(() =>
    apiCall(`${base}/test`, {
      method: 'POST',
      body: { expected_revision: expectedRevision },
      signal,
      schema: testSchema,
    }),
  );
}
export function confirmFirmsConnection(
  body: components['schemas']['FirmsConfirmIn'],
  signal: AbortSignal,
) {
  return scopedMutation(() =>
    apiCall(`${base}/confirm`, { method: 'POST', body, signal, schema: firmsConnectionSchema }),
  );
}
export function removeFirmsConnection(expectedRevision: number, signal: AbortSignal) {
  return scopedMutation(() =>
    apiCall(base, {
      method: 'DELETE',
      body: { expected_revision: expectedRevision },
      signal,
      schema: firmsConnectionSchema,
    }),
  );
}
