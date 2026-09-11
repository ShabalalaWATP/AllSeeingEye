import { profileHandlers } from './handlers.profile';
import { reportJob } from './reportJobFixture';
import { libraryHandlers } from './handlers.library';
/** Default MSW handlers implementing docs/api/AUTH_API.md against the fixtures. */
import { http, HttpResponse } from 'msw';

import { reportHandlers } from './handlers.reports';
import { directionHandlers } from './handlers.direction';
import { scheduleHandlers } from './handlers.schedules';
import { warningHandlers } from './handlers.warning';

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
  conflictCard,
  aviationBoard,
  conflictDetail,
  cyberBoard,
  countries,
  hazardCard,
  hazardDetail,
  jamMap,
  liveEvents,
  maritimeBoard,
  llmProfiles,
  pendingRequests,
  plainUser,
  spaceBoard,
  sources,
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
  ...profileHandlers,
  http.get('/api/auth/mfa', () =>
    HttpResponse.json({
      methods: [],
      available_methods: ['authenticator', 'email'],
      required: false,
    }),
  ),
  http.get('/api/teams', () => HttpResponse.json({ items: [] })),
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

  http.get('/api/admin/llm/profiles', ({ request }) => {
    const gate = requireAdmin(request);
    if (!gate.ok) return gate.response;
    return HttpResponse.json({ items: llmProfiles, encryption_available: true });
  }),

  http.get('/api/admin/llm/connections', ({ request }) => {
    const gate = requireAdmin(request);
    if (!gate.ok) return gate.response;
    return HttpResponse.json({ items: [] });
  }),

  http.post('/api/admin/llm/profiles', async ({ request }) => {
    const gate = requireAdmin(request);
    if (!gate.ok) return gate.response;
    const body = (await request.json()) as Record<string, unknown>;
    const key = typeof body.api_key === 'string' ? body.api_key : '';
    return HttpResponse.json(
      {
        ...llmProfiles[0],
        ...body,
        id: '66666666-6666-4666-8666-666666666666',
        api_key_hint: key.slice(-4),
        api_key: undefined,
      },
      { status: 201 },
    );
  }),

  http.put('/api/admin/llm/profiles/:id', async ({ request, params }) => {
    const gate = requireAdmin(request);
    if (!gate.ok) return gate.response;
    const target = llmProfiles.find((item) => item.id === params.id);
    if (target === undefined) return apiError(404, 'not_found', 'Profile not found.');
    const body = (await request.json()) as Record<string, unknown>;
    const key = typeof body.api_key === 'string' ? body.api_key : '';
    return HttpResponse.json({
      ...target,
      ...body,
      api_key_hint: key === '' ? target.api_key_hint : key.slice(-4),
      api_key: undefined,
    });
  }),

  http.delete('/api/admin/llm/profiles/:id', ({ request }) => {
    const gate = requireAdmin(request);
    if (!gate.ok) return gate.response;
    return new HttpResponse(null, { status: 204 });
  }),

  http.post('/api/admin/llm/profiles/:id/test', ({ request }) => {
    const gate = requireAdmin(request);
    if (!gate.ok) return gate.response;
    return HttpResponse.json({ ok: true, latency_ms: 812.4, model: 'llama3.1:8b', error: null });
  }),

  http.get('/api/admin/sources', ({ request }) => {
    const gate = requireAdmin(request);
    if (!gate.ok) return gate.response;
    return HttpResponse.json({ items: sources });
  }),

  http.post('/api/admin/sources/:id/reset', ({ request, params }) => {
    const gate = requireAdmin(request);
    if (!gate.ok) return gate.response;
    const target = sources.find((item) => item.id === params.id);
    if (target === undefined) return apiError(404, 'not_found', 'Unknown source.');
    return HttpResponse.json({
      ...target.health,
      status: 'idle',
      consecutive_failures: 0,
      last_error: null,
      last_error_at: null,
      next_poll_at: null,
    });
  }),

  ...reportHandlers,

  http.get('/api/trackers/disasters', () => HttpResponse.json({ items: [hazardCard] })),

  http.get('/api/trackers/disasters/:hazard', ({ params }) =>
    params.hazard === 'earthquake'
      ? HttpResponse.json(hazardDetail)
      : apiError(422, 'validation_error', 'Unknown hazard'),
  ),

  http.get('/api/trackers/conflicts', () => HttpResponse.json({ items: [conflictCard] })),
  http.get('/api/trackers/conflict-sources', () => HttpResponse.json({ items: [] })),

  http.get('/api/trackers/aviation', () => HttpResponse.json(aviationBoard)),

  http.get('/api/trackers/aviation/jamming', () => HttpResponse.json(jamMap)),

  http.get('/api/trackers/maritime', () => HttpResponse.json(maritimeBoard)),

  http.get('/api/trackers/space', () => HttpResponse.json(spaceBoard)),

  http.get('/api/trackers/cyber', () => HttpResponse.json(cyberBoard)),

  http.get('/api/trackers/conflicts/:id', ({ params }) =>
    params.id === 'ukraine'
      ? HttpResponse.json(conflictDetail)
      : apiError(404, 'not_found', 'No such conflict'),
  ),

  ...directionHandlers,
  http.get('/api/report-jobs', () => HttpResponse.json({ items: [] })),
  http.get('/api/report-jobs/:id', ({ params }) =>
    HttpResponse.json(reportJob({ id: String(params.id) })),
  ),
  ...libraryHandlers,
  ...warningHandlers,
  ...scheduleHandlers,

  http.get('/api/events', () => HttpResponse.json({ items: liveEvents, count: liveEvents.length })),

  http.get('/api/events/stats', () => HttpResponse.json(storeStats)),

  http.get('/api/countries', () => HttpResponse.json({ items: countries })),

  http.get('/api/capabilities', () => HttpResponse.json({ os_maps: false, os_layers: [] })),

  // The page tests replace the stream client; anything that still reaches the
  // network gets a clean failure instead of an unhandled request.
  http.get('/api/stream', () => new HttpResponse(null, { status: 503 })),
];
