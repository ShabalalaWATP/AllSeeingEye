import { adminHandlers } from './handlers.admin';
import { apiError } from './handlers.responses';
export { apiError } from './handlers.responses';
import { profileHandlers } from './handlers.profile';
import { economyExplainer } from './fixtures.economyExplainer';
import { platformConnections } from './fixtures.researchMetadata';
import { figureBoard } from './fixtures.figures';
import { ukraineHandlers } from './handlers.ukraine';
import { reportJob } from './reportJobFixture';
import { libraryHandlers } from './handlers.library';
/** Default MSW handlers implementing docs/api/AUTH_API.md against the fixtures. */
import { http, HttpResponse } from 'msw';

import { reportHandlers } from './handlers.reports';
import { directionHandlers } from './handlers.direction';
import { scheduleHandlers } from './handlers.schedules';
import { warningHandlers } from './handlers.warning';

import {
  ADMIN_PASSWORD,
  ADMIN_TOKEN,
  BAD_TOKEN,
  CSRF_VALUE,
  GOOD_TOKEN,
  USER_PASSWORD,
  USER_TOKEN,
  WEAK_PASSWORD,
  WEAK_PASSWORD_REASON,
  adminUser,
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
  plainUser,
  spaceBoard,
  storeStats,
  tokenFor,
} from './fixtures';

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
  // The Teams page checks for pending invitations as soon as it mounts.
  http.get('/api/me/team-invitations', () =>
    HttpResponse.json({ items: [], total: 0, offset: 0, limit: 20, next_offset: null }),
  ),
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
      {
        email_available: true,
        message:
          'If the address is registered, check your email for a reset link. You can request another if it does not arrive.',
      },
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

  ...adminHandlers,

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
  http.get('/api/figures', () => HttpResponse.json(figureBoard)),
  ...ukraineHandlers,
  http.get('/api/reference', () =>
    HttpResponse.json({
      items: [],
      retrieved_at: '2026-09-13T18:00:00Z',
      caveat: 'A match is background, not confirmation of identity.',
    }),
  ),
  http.get('/api/sources/connections', () => HttpResponse.json({ items: platformConnections })),

  http.get('/api/trackers/conflicts/:id', ({ params }) =>
    params.id === 'ukraine'
      ? HttpResponse.json(conflictDetail)
      : apiError(404, 'not_found', 'No such conflict'),
  ),

  ...directionHandlers,
  http.post('/api/live-monitor/briefing', () =>
    HttpResponse.json({
      job: reportJob({ status: 'paused' }),
      next_refresh_at: new Date(Date.now() + 86_400_000).toISOString(),
      coverage_note: 'The briefing covers available connected sources only.',
    }),
  ),
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
  http.get('/api/cyber/radar-attacks', () =>
    HttpResponse.json({
      status: 'not_configured',
      fetched_at: null,
      layers: [],
      source_url: 'https://radar.cloudflare.com/',
    }),
  ),

  http.get('/api/economy/explainer', () => HttpResponse.json(economyExplainer)),

  // The page tests replace the stream client; anything that still reaches the
  // network gets a clean failure instead of an unhandled request.
  http.get('/api/stream', () => new HttpResponse(null, { status: 503 })),
];
