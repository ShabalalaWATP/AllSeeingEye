/** MFA challenges and enrolment keys stay in memory, never browser storage. */
import { z } from 'zod';

import { apiCall, apiSend } from './client';
import { tokenResponseSchema } from './schemas';
import type { components } from './types.gen';

export type PendingMfa = components['schemas']['MfaPendingOut'];
export type MfaStatus = components['schemas']['MfaStatusOut'];
export type MfaMethod = PendingMfa['methods'][number];
export type MfaEnrolment = components['schemas']['TotpEnrolOut'];
const methodSchema = z.enum(['authenticator', 'email', 'recovery']);
export const pendingMfaSchema: z.ZodType<PendingMfa> = z.object({
  mfa_required: z.literal(true),
  challenge_token: z.string().min(1),
  expires_at: z.string(),
  methods: z.array(methodSchema),
  enrollment_required: z.boolean(),
  email_sent: z.boolean(),
});
const statusSchema: z.ZodType<MfaStatus> = z.object({
  methods: z.array(methodSchema),
  available_methods: z.array(methodSchema),
  required: z.boolean(),
});
const enrolmentSchema: z.ZodType<MfaEnrolment> = z.object({
  secret: z.string(),
  provisioning_uri: z.string(),
  expires_in: z.number(),
});

export function fetchMfaStatus() {
  return apiCall('/api/auth/mfa', { schema: statusSchema });
}
export function verifyMfa(
  challenge_token: string,
  method: MfaMethod,
  code: string,
  signal?: AbortSignal,
) {
  return apiCall('/api/auth/mfa/verify', {
    method: 'POST',
    body: { challenge_token, method, code },
    ...(signal === undefined ? {} : { signal }),
    schema: tokenResponseSchema,
    auth: false,
  });
}
export function sendMfaEmail(challenge_token: string) {
  return apiCall('/api/auth/mfa/email', {
    method: 'POST',
    body: { challenge_token },
    schema: pendingMfaSchema,
    auth: false,
  });
}
export function enrolLoginApp(challenge_token: string) {
  return apiCall('/api/auth/mfa/enrol-app', {
    method: 'POST',
    body: { challenge_token },
    schema: enrolmentSchema,
    auth: false,
  });
}
export function startEmailMfa(action: 'enrol' | 'disable', password: string) {
  return apiCall(`/api/auth/mfa/email/${action}`, {
    method: 'POST',
    body: { password },
    schema: pendingMfaSchema,
  });
}
export function confirmEmailMfa(
  action: 'enrol' | 'disable',
  challenge_token: string,
  code: string,
) {
  return apiSend(`/api/auth/mfa/email/${action}/confirm`, {
    method: 'POST',
    body: { challenge_token, code },
  });
}
export function startPasswordChangeMfa(password: string) {
  return apiCall('/api/auth/mfa/password-change', {
    method: 'POST',
    body: { password },
    schema: pendingMfaSchema,
  });
}
