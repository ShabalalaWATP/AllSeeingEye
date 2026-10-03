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
