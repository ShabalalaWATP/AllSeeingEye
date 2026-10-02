import { z } from 'zod';

import { apiCall, apiSend } from './client';
import type { components } from './types.gen';

export type EmailPreferences = components['schemas']['EmailPreferencesOut'];
export type EmailInput = components['schemas']['EmailPreferencesIn'];
export type SubscriptionEmail = components['schemas']['SubscriptionEmailIn'];
const emailSchema: z.ZodType<EmailPreferences> = z.object({
  enabled: z.boolean(),
  include_names: z.boolean(),
  available: z.boolean(),
  confirmed: z.boolean(),
  destination: z.string(),
});
const subscriptionSchema: z.ZodType<SubscriptionEmail> = z.object({
  policy: z.enum(['none', 'material_changes', 'every_edition']),
  attention: z.boolean(),
});

export function getEmailPreferences(): Promise<EmailPreferences> {
  return apiCall('/api/me/notifications/email', { schema: emailSchema });
}

export function saveEmailPreferences(body: EmailInput): Promise<void> {
  return apiSend('/api/me/notifications/email', { method: 'PUT', body });
}

export function getSubscriptionEmail(id: string): Promise<SubscriptionEmail> {
  return apiCall(`/api/schedules/${encodeURIComponent(id)}/notifications/email`, {
    schema: subscriptionSchema,
  });
}

export function saveSubscriptionEmail(id: string, body: SubscriptionEmail): Promise<void> {
  return apiSend(`/api/schedules/${encodeURIComponent(id)}/notifications/email`, {
    method: 'PUT',
    body,
  });
}
