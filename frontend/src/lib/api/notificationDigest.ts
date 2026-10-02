import { z } from 'zod';

import { apiCall, apiSend } from './client';
import type { components } from './types.gen';

export type DigestPreferences = components['schemas']['DigestPreferencesIn'];
const schema: z.ZodType<DigestPreferences> = z.object({
  enabled: z.boolean(),
  timezone: z.string(),
  hour: z.number().int().min(0).max(23),
});

export function getDigestPreferences(): Promise<DigestPreferences> {
  return apiCall('/api/me/notifications/digest', { schema });
}

export function saveDigestPreferences(body: DigestPreferences): Promise<void> {
  return apiSend('/api/me/notifications/digest', { method: 'PUT', body });
}
