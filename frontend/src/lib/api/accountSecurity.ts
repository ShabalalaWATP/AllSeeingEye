import { z } from 'zod';
import { apiCall, apiSend } from './client';
import { pendingMfaSchema } from './mfa';
import type { components } from './types.gen';

export type AccountSession = components['schemas']['AccountSessionOut'];
export type AccountSessions = components['schemas']['AccountSessionsOut'];
export type RecoveryStatus = components['schemas']['RecoveryStatusOut'];
export type RecoveryInput = components['schemas']['RecoveryGenerateIn'];
const sessionsSchema: z.ZodType<AccountSessions> = z.object({
  items: z.array(
    z.object({
      id: z.string(),
      current: z.boolean(),
      created_at: z.string(),
      last_active_at: z.string(),
      expires_at: z.string(),
      user_agent: z.string().nullable(),
      ip: z.string().nullable(),
    }),
  ),
  truncated: z.boolean(),
});
const recoverySchema: z.ZodType<RecoveryStatus> = z.object({
  remaining: z.number().int().nonnegative(),
  available: z.boolean(),
});
const codesSchema: z.ZodType<components['schemas']['RecoveryCodesOut']> = z.object({
  codes: z.array(z.string()),
});
export const fetchAccountSessions = () => apiCall('/api/me/sessions', { schema: sessionsSchema });
export const revokeAccountSession = (id: string, signal: AbortSignal) =>
  apiSend(`/api/me/sessions/${encodeURIComponent(id)}`, { method: 'DELETE', signal });
export const revokeOtherSessions = (signal: AbortSignal) =>
  apiSend('/api/me/sessions/revoke-others', { method: 'POST', signal });
export const fetchRecoveryStatus = () =>
  apiCall('/api/auth/mfa/recovery', { schema: recoverySchema });
export const startRecoveryChallenge = (password: string, signal: AbortSignal) =>
  apiCall('/api/auth/mfa/recovery/challenge', {
    method: 'POST',
    body: { password },
    schema: pendingMfaSchema,
    signal,
  });
export const generateRecoveryCodes = (body: RecoveryInput, signal: AbortSignal) =>
  apiCall('/api/auth/mfa/recovery/generate', { method: 'POST', body, schema: codesSchema, signal });
