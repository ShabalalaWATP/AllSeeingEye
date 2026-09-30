import { z } from 'zod';

import { apiCall, apiSend } from './client';
import type { components } from './types.gen';

export type FeedStatus = components['schemas']['FeedStatusOut'];
export type FeedToken = components['schemas']['FeedTokenOut'];

const statusSchema: z.ZodType<FeedStatus> = z.object({
  enabled: z.boolean(),
  include_titles: z.boolean(),
  created_at: z.string().nullable(),
});
const tokenSchema: z.ZodType<FeedToken> = z.object({
  token: z.string(),
  feed_url: z.string(),
  username: z.string(),
});
const path = '/api/me/notifications/feed';

export function getFeedStatus(signal?: AbortSignal): Promise<FeedStatus> {
  return apiCall(path, { schema: statusSchema, ...(signal ? { signal } : {}) });
}

export function enableFeed(includeTitles: boolean): Promise<FeedToken> {
  return apiCall(path, {
    method: 'POST',
    body: { include_titles: includeTitles },
    schema: tokenSchema,
    retryAfterRefresh: false,
  });
}

export function revokeFeed(): Promise<void> {
  return apiSend(path, { method: 'DELETE' });
}
