import { z } from 'zod';
import { scopedMutation } from '@/lib/workspaceAccess';
import { apiCall, apiSend } from './client';
import { reportSummarySchema } from './reports';
import type { components } from './types.gen';

export type LibraryPreference = components['schemas']['LibraryPreferenceOut'];
export type LibraryInput = components['schemas']['LibraryPreferenceIn'];
export type LibraryPage = components['schemas']['LibraryPageOut'];

const preferenceSchema = z.object({
  favourite: z.boolean(),
  tags: z.array(z.string()),
  note: z.string().nullable(),
  updated_at: z.string().nullable(),
}) satisfies z.ZodType<LibraryPreference>;
const pageSchema = z.object({
  items: z.array(z.object({ report: reportSummarySchema, preference: preferenceSchema })),
  total: z.number().int().nonnegative(),
  offset: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
}) satisfies z.ZodType<LibraryPage>;

export function fetchLibrary(offset = 0, favouriteOnly = false, tag = '') {
  const params = new URLSearchParams({
    limit: '20',
    offset: String(offset),
    favourite_only: String(favouriteOnly),
  });
  if (tag.trim()) params.set('tag', tag.trim());
  return apiCall(`/api/me/library?${params}`, { schema: pageSchema });
}
export const fetchLibraryPreference = (id: string) =>
  apiCall(`/api/me/library/${encodeURIComponent(id)}`, { schema: preferenceSchema });
export const saveLibraryPreference = (id: string, body: LibraryInput, signal: AbortSignal) =>
  scopedMutation(() =>
    apiCall(`/api/me/library/${encodeURIComponent(id)}`, {
      method: 'PUT',
      body,
      signal,
      schema: preferenceSchema,
    }),
  );
export const removeLibraryPreference = (id: string, signal: AbortSignal) =>
  scopedMutation(() =>
    apiSend(`/api/me/library/${encodeURIComponent(id)}`, { method: 'DELETE', signal }),
  );
