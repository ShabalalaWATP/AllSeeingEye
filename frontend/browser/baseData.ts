import type { components } from '../src/lib/api/types.gen';
import { reportTemplates } from '../src/test/fixtures.reports';
import { reportMethodology } from '../src/test/fixtures.reportAssessment';
import { serverCapabilities } from '../src/test/fixtures.researchMetadata';
import languageCatalogue from '../src/test/fixtures.languages.json' with { type: 'json' };

import { BROWSER_NOW } from './origin';

export const profile: components['schemas']['ProfileOut'] = {
  display_name: 'Browser Analyst',
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
  reduced_motion: true,
};

const allowance: components['schemas']['ResearchAllowanceOut'] = {
  tier: 1,
  label: 'Level 1',
  limit: 4,
  period: 'week',
  used: 0,
  remaining: 4,
  period_start: BROWSER_NOW.toISOString(),
  resets_at: '2026-10-17T00:00:00Z',
  revision: 0,
};

/** Only the supporting reads used by these journeys; unknown requests fail closed. */
export const baseReads: Readonly<Record<string, unknown>> = {
  '/api/site': { product_page_enabled: false },
  '/api/capabilities': serverCapabilities,
  '/api/me/profile/languages': languageCatalogue,
  '/api/report-methodology': reportMethodology,
  '/api/trackers/conflicts': { items: [] },
  '/api/trackers/disasters': { items: [] },
  '/api/teams': { items: [] },
  '/api/report-jobs': { items: [] },
  '/api/reports/templates': { items: reportTemplates },
  '/api/countries': { items: [] },
  '/api/research-usage/me': allowance,
  '/api/research/briefs': { items: [], limit: 50, offset: 0 },
  '/api/research/presets': { schema_version: 1, items: [], lens_choices: [], lens_rule: '' },
  '/api/auth/mfa': { methods: [], available_methods: ['authenticator'], required: false },
};
