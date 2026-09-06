import { z } from 'zod';
import { apiCall, apiSend } from './client';
import type { components } from './types.gen';

export type SourceTest = components['schemas']['SourceTestOut'];
const testSchema: z.ZodType<SourceTest> = z.object({
  ok: z.boolean(),
  fetched: z.number().int().nonnegative(),
  capped: z.boolean(),
  message: z.string(),
});
export function activateSource(id: string, enabled: boolean, signal: AbortSignal) {
  return apiSend(`/api/admin/sources/${encodeURIComponent(id)}/activation`, {
    method: 'PATCH',
    body: { enabled },
    signal,
  });
}
export function testSource(id: string, signal: AbortSignal) {
  return apiCall(`/api/admin/sources/${encodeURIComponent(id)}/test`, {
    method: 'POST',
    schema: testSchema,
    signal,
  });
}
