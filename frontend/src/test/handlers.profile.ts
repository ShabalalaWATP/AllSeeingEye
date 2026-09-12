import languageCatalogue from './fixtures.languages.json';
import { http, HttpResponse } from 'msw';

import type { Profile } from '@/lib/api/profile';

import { plainUser } from './fixtures';

export const defaultProfile: Profile = {
  display_name: plainUser.display_name,
  timezone: 'UTC',
  date_format: 'day_first',
  research_mode: 'quick',
  research_languages: ['en'],
  research_window_days: 3,
  research_country: null,
  report_language: 'en',
  report_style: 'assessment',
  export_format: 'pdf',
  appearance_theme: 'obsidian',
  reduced_motion: false,
};
export const profileHandlers = [
  http.get('/api/me/profile/languages', () => HttpResponse.json(languageCatalogue)),
  http.get('/api/me/sessions', () => HttpResponse.json({ items: [], truncated: false })),
  http.get('/api/auth/mfa/recovery', () => HttpResponse.json({ remaining: 0, available: false })),
  http.get('/api/me/profile', () => HttpResponse.json(defaultProfile)),
  http.patch('/api/me/profile', async ({ request }) =>
    HttpResponse.json({ ...defaultProfile, ...((await request.json()) as Partial<Profile>) }),
  ),
];
