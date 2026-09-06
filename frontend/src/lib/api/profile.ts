import { z } from 'zod';

import { apiCall } from './client';
import type { components } from './types.gen';

export type Profile = components['schemas']['ProfileOut'];
export type ProfileInput = components['schemas']['ProfileUpdateIn'];
export const profileSchema: z.ZodType<Profile> = z.object({
  display_name: z.string().min(1).max(120),
  timezone: z.string(),
  date_format: z.enum(['day_first', 'month_first', 'iso']),
  research_mode: z.enum(['quick', 'detailed']),
  research_languages: z.array(z.string()).min(1).max(8),
  research_window_days: z.union([z.literal(1), z.literal(3), z.literal(7), z.literal(14)]),
  research_country: z.string().nullable(),
  report_language: z.enum(['en', 'fr', 'de', 'es', 'ar', 'ru', 'uk', 'zh']),
  report_style: z.enum(['briefing', 'assessment']),
  export_format: z.enum(['pdf', 'docx', 'md']),
});

export function fetchProfile(signal: AbortSignal) {
  return apiCall('/api/me/profile', { schema: profileSchema, signal });
}
export function updateProfile(body: ProfileInput, signal: AbortSignal) {
  return apiCall('/api/me/profile', { method: 'PATCH', body, schema: profileSchema, signal });
}
