/** Social listening responses validated at the boundary and typed from OpenAPI. */
import { z } from 'zod';

import { apiCall } from './client';
import { liveEventSchema } from './eventSchemas';
import type { components } from './types.gen';

export type SocialBoard = components['schemas']['SocialBoardOut'];
export type SocialKeyword = components['schemas']['SocialKeywordOut'];

export const socialBoardSchema = z.object({
  total: z.number().int().nonnegative(),
  located: z.number().int().nonnegative(),
  platforms: z.array(
    z.object({
      platform: z.string(),
      instance: z.string(),
      count: z.number().int(),
      located: z.number().int(),
    }),
  ),
  hashtags: z.array(z.object({ tag: z.string(), count: z.number().int() })),
  keywords: z.array(
    z.object({
      term: z.string(),
      count: z.number().int(),
      baseline: z.number().nullable(),
      baseline_hours: z.number().int(),
      ratio: z.number().nullable(),
      burst: z.boolean(),
    }),
  ),
  posts: z.array(liveEventSchema),
  window_start: z.string(),
  window_end: z.string(),
  keyword_hour: z.string(),
}) satisfies z.ZodType<SocialBoard>;

export function fetchSocialBoard(): Promise<SocialBoard> {
  return apiCall('/api/trackers/social', { schema: socialBoardSchema });
}
