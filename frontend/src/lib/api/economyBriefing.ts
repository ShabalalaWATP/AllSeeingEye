import { z } from 'zod';
import { scopedMutation } from '@/lib/workspaceAccess';
import { apiCall } from './client';
import { reportJobSchema } from './reportJobs';
import type { components } from './types.gen';

export type EconomyBriefing = components['schemas']['EconomyBriefingOut'];
export type EconomyDays = EconomyBriefing['window_days'];
export const ECONOMY_PERIODS = [2, 5, 7, 14] as const;

export function parseEconomyDays(raw: string | null): EconomyDays {
  return ECONOMY_PERIODS.find((days) => String(days) === raw) ?? 2;
}

export function ensureEconomyBriefing(
  days: EconomyDays,
  signal: AbortSignal,
): Promise<EconomyBriefing> {
  const schema: z.ZodType<EconomyBriefing> = z
    .object({
      job: reportJobSchema,
      next_refresh_at: z.iso.datetime({ offset: true }),
      coverage_note: z.string(),
      window_days: z.union([z.literal(2), z.literal(5), z.literal(7), z.literal(14)]),
      period_from: z.iso.datetime({ offset: true }),
      period_to: z.iso.datetime({ offset: true }),
    })
    .refine(
      (value) =>
        value.window_days === days &&
        Date.parse(value.period_to) - Date.parse(value.period_from) === days * 86_400_000,
    );
  return scopedMutation(() =>
    apiCall(`/api/economy/briefing?days=${days}`, {
      method: 'POST',
      schema,
      signal,
      retryAfterRefresh: false,
    }),
  );
}
