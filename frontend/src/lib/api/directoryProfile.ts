import { z } from 'zod';

import { apiCall } from './client';

export interface DirectoryProfile {
  user_id: string;
  username: string | null;
  job_title: string | null;
  organisation: string | null;
  biography: string | null;
  country: string | null;
  languages: string[];
  expertise: string[];
  timezone: string | null;
  is_discoverable: boolean;
  show_timezone: boolean;
  revision: number;
  updated_at: string | null;
}

export interface DirectoryUser {
  user_id: string;
  username: string;
  display_name: string;
  job_title: string | null;
  organisation: string | null;
  biography: string | null;
  country: string | null;
  languages: string[];
  expertise: string[];
  timezone: string | null;
}

export interface DirectoryPage {
  items: DirectoryUser[];
  total: number;
  offset: number;
  limit: number;
  next_offset: number | null;
}

const profileSchema: z.ZodType<DirectoryProfile> = z.object({
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
  show_timezone: z.boolean(),
  revision: z.number().int().min(1),
  updated_at: z.string().nullable(),
});
const userSchema: z.ZodType<DirectoryUser> = z.object({
  user_id: z.uuid(),
  username: z.string(),
  display_name: z.string(),
  job_title: z.string().nullable(),
  organisation: z.string().nullable(),
  biography: z.string().nullable(),
  country: z.string().nullable(),
  languages: z.array(z.string()),
  expertise: z.array(z.string()),
  timezone: z.string().nullable(),
});
const pageSchema: z.ZodType<DirectoryPage> = z.object({
  items: z.array(userSchema),
  total: z.number().int().nonnegative(),
  offset: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  next_offset: z.number().int().nonnegative().nullable(),
});

export function getDirectoryProfile(): Promise<DirectoryProfile> {
  return apiCall('/api/me/directory-profile', { schema: profileSchema });
}

export type DirectoryProfileChanges = Partial<
  Omit<DirectoryProfile, 'user_id' | 'revision' | 'updated_at' | 'timezone'>
> & { timezone?: string | null; expected_revision?: number };

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
