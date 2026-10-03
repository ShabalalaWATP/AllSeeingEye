import languageCatalogue from './fixtures.languages.json';
import { http, HttpResponse } from 'msw';

import type { Profile } from '@/lib/api/profile';

import { defaultProfile } from './fixtures.profile';

export { defaultProfile } from './fixtures.profile';

export const profileHandlers = [
  http.get('/api/me/profile/languages', () => HttpResponse.json(languageCatalogue)),
  http.get('/api/me/sessions', () => HttpResponse.json({ items: [], truncated: false })),
  http.get('/api/auth/mfa/recovery', () => HttpResponse.json({ remaining: 0, available: false })),
  http.get('/api/me/profile', () => HttpResponse.json(defaultProfile)),
  http.patch('/api/me/profile', async ({ request }) =>
    HttpResponse.json({ ...defaultProfile, ...((await request.json()) as Partial<Profile>) }),
  ),
];
