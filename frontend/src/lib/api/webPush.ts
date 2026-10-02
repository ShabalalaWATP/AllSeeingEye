import { z } from 'zod';

import { apiCall, apiSend } from './client';
import type { components } from './types.gen';

export type PushSettings = components['schemas']['PushSettingsOut'];
export type PushDevice = components['schemas']['PushDeviceOut'];
export type PushInput = components['schemas']['PushSubscriptionIn'];
const device: z.ZodType<PushDevice> = z.object({
  id: z.string(),
  endpoint_hash: z.string(),
  created_at: z.string(),
});
const settings: z.ZodType<PushSettings> = z.object({
  available: z.boolean(),
  public_key: z.string().nullable(),
  devices: z.array(device),
});

export function getPushSettings(): Promise<PushSettings> {
  return apiCall('/api/me/notifications/push', { schema: settings });
}

export function registerPush(body: PushInput): Promise<PushDevice> {
  return apiCall('/api/me/notifications/push', { method: 'POST', body, schema: device });
}

export function removePush(id: string): Promise<void> {
  return apiSend(`/api/me/notifications/push/${encodeURIComponent(id)}`, { method: 'DELETE' });
}
