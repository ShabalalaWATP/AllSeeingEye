import { z } from 'zod';

import { scopedMutation } from '@/lib/workspaceAccess';
import { apiCall } from './client';
import { reportJobSchema } from './reportJobs';
import type { components } from './types.gen';

export type DailyBriefing = components['schemas']['DailyBriefingOut'];

const dailyBriefingSchema: z.ZodType<DailyBriefing> = z.object({
  job: reportJobSchema,
  next_refresh_at: z.iso.datetime({ offset: true }),
  coverage_note: z.string(),
});

/** The server reuses the daily job, including across tabs and page visits. */
export function ensureDailyBriefing(signal: AbortSignal): Promise<DailyBriefing> {
  return requestBriefing('/api/live-monitor/briefing', signal);
}

export function ensureEconomyBriefing(signal: AbortSignal): Promise<DailyBriefing> {
  return requestBriefing('/api/economy/briefing', signal);
}

function requestBriefing(
  path: '/api/live-monitor/briefing' | '/api/economy/briefing',
  signal: AbortSignal,
): Promise<DailyBriefing> {
  return scopedMutation(() =>
    apiCall(path, {
      method: 'POST',
      schema: dailyBriefingSchema,
      signal,
      retryAfterRefresh: false,
    }),
  );
}
