/** Auth endpoints, with explicit bearer ownership for activity and verification. */
import { z } from 'zod';

import { csrfHeaders } from '@/lib/csrf';
import { sessionActivitySchema, type SessionActivity } from '@/lib/sessionActivity';

import { pendingMfaSchema, type PendingMfa } from './mfa';
import { apiCall, apiOptional, apiSend } from './client';
import { messageResponseSchema, tokenResponseSchema, userSchema } from './schemas';
import type { TokenResponse, User } from './schemas';
import type { components } from './types.gen';

export type PasswordRecoveryResult = components['schemas']['ForgotPasswordOut'];
const passwordRecoverySchema: z.ZodType<PasswordRecoveryResult> = z.object({
  message: z.string(),
  email_available: z.boolean(),
});

export function login(email: string, password: string): Promise<TokenResponse | PendingMfa> {
  return apiCall('/api/auth/login', {
    method: 'POST',
    body: { email, password },
    schema: z.union([tokenResponseSchema, pendingMfaSchema]),
    auth: false,
  });
}

export function refreshSession(): Promise<TokenResponse> {
  return apiCall('/api/auth/refresh', {
    method: 'POST',
    headers: csrfHeaders(),
    schema: tokenResponseSchema,
    auth: false,
  });
}

export function logout(familyId?: string): Promise<void> {
  return apiSend('/api/auth/logout', {
    method: 'POST',
    headers: {
      ...csrfHeaders(),
      ...(familyId === undefined ? {} : { 'X-ASE-Session-Family': familyId }),
    },
    auth: false,
  });
}

/** Check the original family's server deadline without revoking a family kept live elsewhere. */
export async function checkIdleExpiry(familyId: string): Promise<SessionActivity | null> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 10_000);
  try {
    return await apiOptional('/api/auth/logout', {
      method: 'POST',
      headers: { ...csrfHeaders(), 'X-ASE-Session-Family': familyId, 'X-ASE-Idle-Expired': '1' },
      schema: sessionActivitySchema,
      auth: false,
      signal: controller.signal,
    });
  } finally {
    window.clearTimeout(timeout);
  }
}

/** Never replay against whichever login happens to own the global store later. */
export function recordActivity(accessToken: string): Promise<SessionActivity> {
  return apiCall('/api/auth/activity', {
    method: 'POST',
    headers: { ...csrfHeaders(), Authorization: `Bearer ${accessToken}` },
    schema: sessionActivitySchema,
    auth: false,
  });
}

export interface AccountRequestInput {
  email: string;
  display_name: string;
  reason?: string;
}

export async function requestAccount(input: AccountRequestInput): Promise<string> {
  const result = await apiCall('/api/auth/request-account', {
    method: 'POST',
    body: input,
    schema: messageResponseSchema,
    auth: false,
  });
  return result.message;
}

export function forgotPassword(email: string): Promise<PasswordRecoveryResult> {
  return apiCall('/api/auth/forgot-password', {
    method: 'POST',
    body: { email },
    schema: passwordRecoverySchema,
    auth: false,
  });
}

export function setPassword(token: string, newPassword: string): Promise<void> {
  return apiSend('/api/auth/set-password', {
    method: 'POST',
    body: { token, new_password: newPassword },
    auth: false,
  });
}

export function fetchMe(): Promise<User> {
  return apiCall('/api/me', { schema: userSchema });
}

/** Verify exactly this session. A stale response must not refresh or clear a newer login. */
export function verifySession(accessToken: string, signal: AbortSignal): Promise<User> {
  return apiCall('/api/me', {
    auth: false,
    headers: { Authorization: `Bearer ${accessToken}` },
    signal,
    schema: userSchema,
  });
}
