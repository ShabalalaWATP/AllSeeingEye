/** API client for the bounded, plain-text team board and team overview. */
import { z } from 'zod';

import { apiCall, apiSend } from './client';
import type { components } from './types.gen';

export type TeamBoardPost = components['schemas']['TeamBoardPostOut'];
export type TeamBoardPage = components['schemas']['TeamBoardPageOut'];
export type TeamBoardUnread = components['schemas']['TeamBoardUnreadOut'];
export type TeamDashboard = components['schemas']['TeamDashboardOut'];
export type TeamDashboardAction = components['schemas']['TeamDashboardActionOut'];

const timestamp = z.string();
const postSchema = z.object({
  id: z.uuid(),
  team_id: z.uuid(),
  author_id: z.uuid(),
  author_name: z.string(),
  text: z.string(),
  created_at: timestamp,
  updated_at: timestamp,
  edited_at: timestamp.nullable(),
  parent_id: z.uuid().nullable(),
  is_pinned: z.boolean(),
  deleted_at: timestamp.nullable(),
  removal: z.enum(['author', 'moderator']).nullable(),
  revision: z.number().int().min(1),
}) satisfies z.ZodType<TeamBoardPost>;
const pageSchema = z.object({
  items: z.array(postSchema),
  replies: z.array(postSchema),
  total: z.number().int().nonnegative(),
  offset: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  next_offset: z.number().int().nonnegative().nullable(),
  unread_count: z.number().int().nonnegative(),
}) satisfies z.ZodType<TeamBoardPage>;
const unreadSchema = z.object({
  unread_count: z.number().int().nonnegative(),
}) satisfies z.ZodType<TeamBoardUnread>;
const dashboardSchema = z.object({
  team: z.object({
    id: z.uuid(),
    name: z.string(),
    description: z.string().nullable(),
    is_active: z.boolean(),
    role: z.enum(['member', 'manager']).nullable(),
    member_count: z.number().int().nonnegative(),
  }),
  pinned: z.array(postSchema),
  unread_count: z.number().int().nonnegative(),
  recent_reports: z.array(
    z.object({
      id: z.uuid(),
      title: z.string(),
      template: z.string(),
      status: z.string(),
      latest_version: z.number().int().positive(),
      created_at: timestamp,
    }),
  ),
  upcoming_runs: z.array(
    z.object({
      schedule_id: z.uuid(),
      name: z.string(),
      cadence: z.string(),
      next_run_at: timestamp,
    }),
  ),
  action_items: z.array(
    z.object({
      kind: z.enum(['owner_not_member', 'edition_failed', 'edition_blocked']),
      schedule_id: z.uuid(),
      schedule_name: z.string(),
      occurred_at: timestamp,
      edition_id: z.uuid().nullable(),
    }),
  ),
}) satisfies z.ZodType<TeamDashboard>;

function team(teamId: string): string {
  return `/api/teams/${encodeURIComponent(teamId)}`;
}

function post(teamId: string, postId: string, action = ''): string {
  return `${team(teamId)}/board/posts/${encodeURIComponent(postId)}${action}`;
}

export function listBoardPosts(
  teamId: string,
  offset = 0,
  limit = 20,
  signal?: AbortSignal,
): Promise<TeamBoardPage> {
  return apiCall(`${team(teamId)}/board/posts?limit=${limit}&offset=${offset}`, {
    schema: pageSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export function createBoardPost(
  teamId: string,
  text: string,
  parentId?: string,
): Promise<TeamBoardPost> {
  return apiCall(`${team(teamId)}/board/posts`, {
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
  return apiCall(post(teamId, postId), {
    method: 'PATCH',
    body: { text, expected_revision: expectedRevision },
    schema: postSchema,
  });
}

/** Pin or unpin. Moderating someone else's post requires a reason kept in the audit log. */
export function pinBoardPost(
  teamId: string,
  postId: string,
  pinned: boolean,
  expectedRevision: number,
  reason?: string,
): Promise<TeamBoardPost> {
  return apiCall(post(teamId, postId, '/pin'), {
    method: 'POST',
    body: { pinned, expected_revision: expectedRevision, ...(reason ? { reason } : {}) },
    schema: postSchema,
  });
}

/** Author removal uses DELETE; moderator removal sends its reason in the request body. */
export function removeBoardPost(
  teamId: string,
  postId: string,
  expectedRevision: number,
  reason?: string,
): Promise<unknown> {
  if (!reason) {
    return apiSend(`${post(teamId, postId)}?expected_revision=${expectedRevision}`, {
      method: 'DELETE',
    });
  }
  return apiCall(post(teamId, postId, '/remove'), {
    method: 'POST',
    body: { expected_revision: expectedRevision, reason },
    schema: postSchema,
  });
}

export function markBoardRead(teamId: string, lastSeenPostId: string): Promise<TeamBoardUnread> {
  return apiCall(`${team(teamId)}/board/read`, {
    method: 'POST',
    body: { last_seen_post_id: lastSeenPostId },
    schema: unreadSchema,
  });
}

export function getTeamDashboard(teamId: string, signal?: AbortSignal): Promise<TeamDashboard> {
  return apiCall(`${team(teamId)}/dashboard`, {
    schema: dashboardSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}
