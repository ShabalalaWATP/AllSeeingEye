/** TOTP secrets are returned only during enrolment and stay in component memory. */
import { z } from 'zod';

import { apiCall, apiSend } from './client';
import type { components } from './types.gen';

export type TotpStatus = components['schemas']['TotpStatusOut'];
export type TotpEnrolment = components['schemas']['TotpEnrolOut'];
const statusSchema: z.ZodType<TotpStatus> = z.object({
  enabled: z.boolean(),
  available: z.boolean(),
});
const enrolmentSchema: z.ZodType<TotpEnrolment> = z.object({
  secret: z.string(),
  provisioning_uri: z.string(),
  expires_in: z.number(),
});

export function fetchTotpStatus(): Promise<TotpStatus> {
  return apiCall('/api/auth/totp', { schema: statusSchema });
}

export function enrolTotp(password: string): Promise<TotpEnrolment> {
  return apiCall('/api/auth/totp/enrol', {
    method: 'POST',
    body: { password },
    schema: enrolmentSchema,
  });
}

export function confirmTotp(code: string): Promise<void> {
  return apiSend('/api/auth/totp/confirm', { method: 'POST', body: { code } });
}

export function disableTotp(password: string, code: string): Promise<void> {
  return apiSend('/api/auth/totp/disable', { method: 'POST', body: { password, code } });
}
