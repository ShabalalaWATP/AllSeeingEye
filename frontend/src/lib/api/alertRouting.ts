import { z } from 'zod';

import { scopedMutation } from '@/lib/workspaceAccess';
import { apiCall, apiSend } from './client';
import type { components } from './types.gen';

const routeSchema = z.object({
  indicator_id: z.uuid(),
  configured_by: z.uuid(),
  email_enabled: z.boolean(),
  webhook_id: z.uuid().nullable(),
  revision: z.number().int(),
  can_manage: z.boolean(),
});
const destinationSchema = z.object({
  id: z.uuid(),
  name: z.string(),
  created_by: z.uuid(),
  team_id: z.uuid().nullable(),
  enabled: z.boolean(),
  created_at: z.string(),
});
const capabilitiesSchema = z.object({
  installation_copy_enabled: z.boolean(),
  in_app_required: z.boolean(),
  installation_copy_notice: z.string(),
});

export type AlertRoute = components['schemas']['AlertRoutingOut'];
export type AlertDestination = components['schemas']['AlertWebhookDestinationOut'];

export function getRoutingCapabilities() {
  return apiCall('/api/warning/notification-capabilities', { schema: capabilitiesSchema });
}
export function getAlertRoute(id: string): Promise<AlertRoute> {
  return apiCall(`/api/warning/indicators/${encodeURIComponent(id)}/notifications`, {
    schema: routeSchema,
  });
}
export function saveAlertRoute(
  id: string,
  body: components['schemas']['AlertRoutingIn'],
): Promise<AlertRoute> {
  return scopedMutation(() =>
    apiCall(`/api/warning/indicators/${encodeURIComponent(id)}/notifications`, {
      method: 'PUT',
      body,
      schema: routeSchema,
    }),
  );
}
export async function getAlertDestinations(teamId: string | null): Promise<AlertDestination[]> {
  const query = teamId ? `?team_id=${encodeURIComponent(teamId)}` : '';
  return (
    await apiCall(`/api/warning/webhook-destinations${query}`, {
      schema: z.object({ items: z.array(destinationSchema) }),
    })
  ).items;
}
export function registerAlertDestination(
  body: components['schemas']['AlertDestinationIn'],
): Promise<AlertDestination> {
  return scopedMutation(() =>
    apiCall('/api/warning/webhook-destinations', {
      method: 'POST',
      body,
      schema: destinationSchema,
    }),
  );
}
export function removeAlertDestination(id: string): Promise<void> {
  return scopedMutation(() =>
    apiSend(`/api/warning/webhook-destinations/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    }),
  );
}
