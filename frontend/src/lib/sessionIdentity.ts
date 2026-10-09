import { z } from 'zod';

import { ApiError } from './api/errors';
import type { TokenResponse } from './api/schemas';

const identityClaims = z.object({
  sub: z.string().trim().min(1),
  sid: z.string().trim().min(1),
  typ: z.literal('access'),
});

export interface SessionIdentity {
  userId: string;
  familyId: string;
}

/**
 * Reads continuity metadata only. This does not authenticate a JWT: the server
 * still verifies its signature, expiry, account and family on every request.
 */
export function sessionIdentity(token: string): SessionIdentity | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3 || !parts[0] || !parts[1] || !parts[2]) return null;
    const payload: unknown = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
    const claims = identityClaims.safeParse(payload);
    return claims.success ? { userId: claims.data.sub, familyId: claims.data.sid } : null;
  } catch {
    return null;
  }
}

export function responseIdentity(token: TokenResponse): SessionIdentity {
  const identity = sessionIdentity(token.access_token);
  if (identity?.userId !== token.user.id) {
    throw new ApiError(502, 'invalid_response', 'The server sent an unexpected session response.');
  }
  return identity;
}
