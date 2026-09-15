/** Small API client for the bounded, plain-text team board. */
import { z } from 'zod';

import { apiCall, apiSend } from './client';

export interface TeamBoardPost {
  id: string;
  team_id: string;
  author_id: string;
  author_name: string;
  text: string;
  created_at: string;
  updated_at: string;
  parent_id: string | null;
  is_pinned: boolean;
  deleted_at: string | null;
  revision: number;
}

export interface TeamBoardPage {
  items: TeamBoardPost[];
  total: number;
  offset: number;
  limit: number;
  next_offset: number | null;
}

const postSchema: z.ZodType<TeamBoardPost> = z.object({
  id: z.uuid(),
  team_id: z.uuid(),
  author_id: z.uuid(),
  author_name: z.string(),
  text: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  parent_id: z.uuid().nullable(),
  is_pinned: z.boolean(),
  deleted_at: z.string().nullable(),
  revision: z.number().int().min(1),
});
const pageSchema: z.ZodType<TeamBoardPage> = z.object({
  items: z.array(postSchema),
  total: z.number().int().nonnegative(),
  offset: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  next_offset: z.number().int().nonnegative().nullable(),
});

function base(teamId: string): string {
  return `/api/teams/${encodeURIComponent(teamId)}/board/posts`;
}

export function listBoardPosts(teamId: string, limit = 20, offset = 0): Promise<TeamBoardPage> {
  return apiCall(`${base(teamId)}?limit=${limit}&offset=${offset}`, { schema: pageSchema });
}

export function createBoardPost(
  teamId: string,
  text: string,
  parentId?: string,
): Promise<TeamBoardPost> {
  return apiCall(base(teamId), {
    method: 'POST',
    body: { text, ...(parentId === undefined ? {} : { parent_id: parentId }) },
    schema: postSchema,
  });
}

export function editBoardPost(
  teamId: string,
  postId: string,
  text: string,
  expectedRevision: number,
): Promise<TeamBoardPost> {
  return apiCall(`${base(teamId)}/${encodeURIComponent(postId)}`, {
    method: 'PATCH',
    body: { text, expected_revision: expectedRevision },
    schema: postSchema,
  });
}

export function pinBoardPost(
  teamId: string,
  postId: string,
  pinned: boolean,
  expectedRevision: number,
): Promise<TeamBoardPost> {
  return apiCall(`${base(teamId)}/${encodeURIComponent(postId)}/pin`, {
    method: 'POST',
    body: { pinned, expected_revision: expectedRevision },
    schema: postSchema,
  });
}

export function deleteBoardPost(
  teamId: string,
  postId: string,
  expectedRevision: number,
): Promise<void> {
  return apiSend(
    `${base(teamId)}/${encodeURIComponent(postId)}?expected_revision=${expectedRevision}`,
    { method: 'DELETE' },
  );
}
