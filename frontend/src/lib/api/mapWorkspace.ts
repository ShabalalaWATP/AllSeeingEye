import { z } from 'zod';

import { scopedMutation } from '@/lib/workspaceAccess';

import { apiCall, apiSend } from './client';
import type { components } from './types.gen';

export const mapWorkspaceDocumentSchema = z.object({
  id: z.uuid(),
  kind: z.enum(['drawings', 'radio']),
  title: z.string(),
  payload: z.record(z.string(), z.unknown()),
  revision: z.number().int().positive(),
  created_by: z.uuid(),
  team_id: z.uuid().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
}) satisfies z.ZodType<components['schemas']['MapWorkspaceOut']>;

export type MapWorkspaceDocument = z.infer<typeof mapWorkspaceDocumentSchema>;
export type MapWorkspaceKind = MapWorkspaceDocument['kind'];
const base = '/api/map/workspaces';

export function listMapWorkspaceDocuments(
  kind: MapWorkspaceKind,
  signal?: AbortSignal,
  page?: { offset?: number; limit?: number },
) {
  const query = new URLSearchParams({ kind });
  if (page?.offset !== undefined) query.set('offset', String(page.offset));
  if (page?.limit !== undefined) query.set('limit', String(page.limit));
  return apiCall(`${base}?${query.toString()}`, {
    schema: z.array(mapWorkspaceDocumentSchema),
    ...(signal ? { signal } : {}),
  });
}

export function getMapWorkspaceDocument(id: string, signal?: AbortSignal) {
  return apiCall(`${base}/${encodeURIComponent(id)}`, {
    schema: mapWorkspaceDocumentSchema,
    ...(signal ? { signal } : {}),
  });
}

export function createMapWorkspaceDocument(
  body: components['schemas']['MapWorkspaceCreateIn'],
  signal?: AbortSignal,
) {
  return scopedMutation(() =>
    apiCall(base, {
      method: 'POST',
      body,
      schema: mapWorkspaceDocumentSchema,
      ...(signal ? { signal } : {}),
    }),
  );
}

export function updateMapWorkspaceDocument(
  id: string,
  body: components['schemas']['MapWorkspaceUpdateIn'],
  signal?: AbortSignal,
) {
  return scopedMutation(() =>
    apiCall(`${base}/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body,
      schema: mapWorkspaceDocumentSchema,
      ...(signal ? { signal } : {}),
    }),
  );
}

export function removeMapWorkspaceDocument(id: string, signal?: AbortSignal) {
  return scopedMutation(() =>
    apiSend(`${base}/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      ...(signal ? { signal } : {}),
    }),
  );
}
