import { HttpResponse } from 'msw';
import { ADMIN_TOKEN, USER_TOKEN } from './fixtures';

export function apiError(
  status: number,
  code: string,
  message: string,
  fields?: Record<string, string>,
  headers?: Record<string, string>,
) {
  const init: { status: number; headers?: Record<string, string> } = { status };
  if (headers !== undefined) init.headers = headers;
  return HttpResponse.json(
    { error: fields === undefined ? { code, message } : { code, message, fields } },
    init,
  );
}

type ErrorResponse = ReturnType<typeof apiError>;

type Gate = { ok: true } | { ok: false; response: ErrorResponse };

/** Returns the bearer gate result for admin routes. */
export function requireAdmin(request: Request): Gate {
  const header = request.headers.get('Authorization');
  if (header === `Bearer ${ADMIN_TOKEN}`) return { ok: true };
  if (header === `Bearer ${USER_TOKEN}`) {
    return { ok: false, response: apiError(403, 'forbidden', 'Admin role required.') };
  }
  return { ok: false, response: apiError(401, 'unauthenticated', 'Sign in required.') };
}
