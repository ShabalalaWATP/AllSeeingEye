/** Default MSW handlers implementing docs/api/AUTH_API.md against the fixtures. */
import { http, HttpResponse } from 'msw';

import {
  ACTIVATION_LINK,
  ADMIN_PASSWORD,
  ADMIN_TOKEN,
  BAD_TOKEN,
  CSRF_VALUE,
  GOOD_TOKEN,
  RESET_LINK,
  USER_PASSWORD,
  USER_TOKEN,
  WEAK_PASSWORD,
  WEAK_PASSWORD_REASON,
  adminUser,
  auditPageOne,
  auditPageTwo,
  countries,
  liveEvents,
  pendingRequests,
  plainUser,
  storeStats,
  tokenFor,
} from './fixtures';

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
function requireAdmin(request: Request): Gate {
  const header = request.headers.get('Authorization');
  if (header === `Bearer ${ADMIN_TOKEN}`) return { ok: true };
  if (header === `Bearer ${USER_TOKEN}`) {
    return { ok: false, response: apiError(403, 'forbidden', 'Admin role required.') };
  }
  return { ok: false, response: apiError(401, 'unauthenticated', 'Sign in required.') };
}

interface LoginBody {
  email?: string;
  password?: string;
}

interface SetPasswordBody {
  token?: string;
  new_password?: string;
}

export const handlers = [
  http.post('/api/auth/login', async ({ request }) => {
    const body = (await request.json()) as LoginBody;
    if (body.email === adminUser.email && body.password === ADMIN_PASSWORD) {
      return HttpResponse.json(tokenFor(adminUser));
    }
    if (body.email === plainUser.email && body.password === USER_PASSWORD) {
      return HttpResponse.json(tokenFor(plainUser));
    }
    return apiError(401, 'invalid_credentials', 'Incorrect email or password.');
  }),

  http.post('/api/auth/refresh', ({ request }) => {
    if (request.headers.get('X-CSRF-Token') !== CSRF_VALUE) {
      return apiError(401, 'invalid_refresh', 'The session has expired.');
    }
    return HttpResponse.json(tokenFor(adminUser));
  }),

  http.post('/api/auth/logout', () => new HttpResponse(null, { status: 204 })),

  http.post('/api/auth/request-account', () =>
    HttpResponse.json(
      { message: 'If the address is eligible, an administrator will review the request.' },
      { status: 202 },
    ),
  ),

  http.post('/api/auth/forgot-password', () =>
    HttpResponse.json(
      { message: 'If the address is registered, a reset link has been issued.' },
      { status: 202 },
    ),
  ),

  http.post('/api/auth/set-password', async ({ request }) => {
    const body = (await request.json()) as SetPasswordBody;
    if (body.token === BAD_TOKEN) {
      return apiError(400, 'invalid_token', 'The token is invalid or has expired.');
    }
    if (body.new_password === WEAK_PASSWORD) {
      return apiError(422, 'weak_password', 'The password is too weak.', {
        new_password: WEAK_PASSWORD_REASON,
      });
    }
    if (body.token === GOOD_TOKEN) return new HttpResponse(null, { status: 204 });
    return apiError(400, 'invalid_token', 'The token is invalid or has expired.');
  }),

  http.get('/api/me', ({ request }) => {
    const header = request.headers.get('Authorization');
    if (header === `Bearer ${ADMIN_TOKEN}`) return HttpResponse.json(adminUser);
    if (header === `Bearer ${USER_TOKEN}`) return HttpResponse.json(plainUser);
    return apiError(401, 'unauthenticated', 'Sign in required.');
  }),

  http.get('/api/admin/account-requests', ({ request }) => {
    const gate = requireAdmin(request);
    if (!gate.ok) return gate.response;
    return HttpResponse.json({ items: pendingRequests });
  }),

  http.post('/api/admin/account-requests/:id/approve', async ({ request, params }) => {
    const gate = requireAdmin(request);
    if (!gate.ok) return gate.response;
    const body = (await request.json()) as { role?: 'user' | 'admin' };
    const target = pendingRequests.find((item) => item.id === params.id);
    if (target === undefined) return apiError(404, 'not_found', 'Request not found.');
    return HttpResponse.json({
      user: {
        ...plainUser,
        id: target.id,
        email: target.email,
        display_name: target.display_name,
        role: body.role ?? 'user',
        is_active: false,
      },
      activation_link: ACTIVATION_LINK,
      expires_at: '2026-09-11T12:00:00Z',
    });
  }),

  http.post('/api/admin/account-requests/:id/reject', ({ request, params }) => {
    const gate = requireAdmin(request);
    if (!gate.ok) return gate.response;
    const target = pendingRequests.find((item) => item.id === params.id);
    if (target === undefined) return apiError(404, 'not_found', 'Request not found.');
    return new HttpResponse(null, { status: 204 });
  }),

  http.get('/api/admin/users', ({ request }) => {
    const gate = requireAdmin(request);
    if (!gate.ok) return gate.response;
    return HttpResponse.json({ items: [adminUser, plainUser] });
  }),

  http.patch('/api/admin/users/:id', async ({ request, params }) => {
    const gate = requireAdmin(request);
    if (!gate.ok) return gate.response;
    if (params.id === adminUser.id) {
      return apiError(409, 'self_modification', 'You cannot modify your own account.');
    }
    if (params.id !== plainUser.id) return apiError(404, 'not_found', 'User not found.');
    const patch = (await request.json()) as { role?: 'user' | 'admin'; is_active?: boolean };
    return HttpResponse.json({ ...plainUser, ...patch });
  }),

  http.post('/api/admin/users/:id/reset-link', ({ request, params }) => {
    const gate = requireAdmin(request);
    if (!gate.ok) return gate.response;
    if (params.id !== plainUser.id && params.id !== adminUser.id) {
      return apiError(404, 'not_found', 'User not found.');
    }
    return HttpResponse.json({ reset_link: RESET_LINK, expires_at: '2026-09-04T10:30:00Z' });
  }),

  http.get('/api/admin/audit-log', ({ request }) => {
    const gate = requireAdmin(request);
    if (!gate.ok) return gate.response;
    const before = new URL(request.url).searchParams.get('before');
    if (before === null) return HttpResponse.json({ items: auditPageOne, next_before: 118 });
    return HttpResponse.json({ items: auditPageTwo, next_before: null });
  }),

  http.get('/api/events', () => HttpResponse.json({ items: liveEvents, count: liveEvents.length })),

  http.get('/api/events/stats', () => HttpResponse.json(storeStats)),

  http.get('/api/countries', () => HttpResponse.json({ items: countries })),

  http.get('/api/capabilities', () => HttpResponse.json({ os_maps: false, os_layers: [] })),

  // The page tests replace the stream client; anything that still reaches the
  // network gets a clean failure instead of an unhandled request.
  http.get('/api/stream', () => new HttpResponse(null, { status: 503 })),
];
