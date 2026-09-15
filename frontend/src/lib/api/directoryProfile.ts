/** Owner directory profile, avatar and opt-in people search; responses are validated. */
import { z } from 'zod';

import { apiBlob, apiCall } from './client';
import type { components } from './types.gen';

export type DirectoryProfile = components['schemas']['DirectoryProfileOut'];
export type DirectoryUser = components['schemas']['DirectoryUserOut'];
export type DirectoryPage = components['schemas']['DirectoryPageOut'];
export type DirectoryField = components['schemas']['DirectoryField'];
export type DirectoryProfileChanges = components['schemas']['DirectoryProfileUpdateIn'];

export const DIRECTORY_FIELDS = [
  'job_title',
  'organisation',
  'biography',
  'country',
  'languages',
  'expertise',
  'timezone',
] as const satisfies readonly DirectoryField[];

/** Accepted upload size, mirroring the server limit so obvious mistakes fail early. */
export const MAX_AVATAR_BYTES = 2 * 1024 * 1024;
export const AVATAR_TYPES = ['image/jpeg', 'image/png', 'image/webp'] as const;

// Only same-origin, versioned avatar routes are accepted from the server.
const avatarUrlSchema = z
  .string()
  .regex(/^\/api\/directory\/users\/[0-9a-f-]{36}\/avatar\?v=[0-9a-f]{16}$/)
  .nullable();

const profileSchema = z.object({
  user_id: z.uuid(),
  username: z.string().nullable(),
  job_title: z.string().nullable(),
  organisation: z.string().nullable(),
  biography: z.string().nullable(),
  country: z.string().nullable(),
  languages: z.array(z.string()),
  expertise: z.array(z.string()),
  timezone: z.string().nullable(),
  is_discoverable: z.boolean(),
  visible_fields: z.array(z.enum(DIRECTORY_FIELDS)),
  avatar_url: avatarUrlSchema,
  revision: z.number().int().min(1),
  updated_at: z.string().nullable(),
}) satisfies z.ZodType<DirectoryProfile>;

const userSchema = z.object({
  user_id: z.uuid(),
  username: z.string(),
  display_name: z.string(),
  avatar_url: avatarUrlSchema,
  job_title: z.string().nullable(),
  organisation: z.string().nullable(),
  biography: z.string().nullable(),
  country: z.string().nullable(),
  languages: z.array(z.string()),
  expertise: z.array(z.string()),
  timezone: z.string().nullable(),
}) satisfies z.ZodType<DirectoryUser>;

const pageSchema = z.object({
  items: z.array(userSchema),
  total: z.number().int().nonnegative(),
  offset: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  next_offset: z.number().int().nonnegative().nullable(),
}) satisfies z.ZodType<DirectoryPage>;

export function getDirectoryProfile(): Promise<DirectoryProfile> {
  return apiCall('/api/me/directory-profile', { schema: profileSchema });
}

export function updateDirectoryProfile(body: DirectoryProfileChanges): Promise<DirectoryProfile> {
  return apiCall('/api/me/directory-profile', {
    method: 'PATCH',
    body,
    schema: profileSchema,
  });
}

export function searchDirectory(query: string, limit = 20, offset = 0): Promise<DirectoryPage> {
  const params = new URLSearchParams({ q: query, limit: String(limit), offset: String(offset) });
  return apiCall(`/api/directory/users?${params.toString()}`, { schema: pageSchema });
}

export function uploadDirectoryAvatar(file: Blob): Promise<DirectoryProfile> {
  return apiCall('/api/me/directory-profile/avatar', {
    method: 'PUT',
    rawBody: file,
    schema: profileSchema,
  });
}

export function removeDirectoryAvatar(): Promise<DirectoryProfile> {
  return apiCall('/api/me/directory-profile/avatar', { method: 'DELETE', schema: profileSchema });
}

/** Avatars need the bearer token, so they are fetched as blobs rather than plain image URLs. */
export function fetchDirectoryAvatar(avatarUrl: string, signal?: AbortSignal): Promise<Blob> {
  return apiBlob(avatarUrl, signal ? { signal } : {});
}
