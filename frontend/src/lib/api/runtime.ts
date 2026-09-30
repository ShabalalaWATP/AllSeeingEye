import { z } from 'zod';

import { apiCall } from './client';
import type { components } from './types.gen';

export type RuntimeHealth = components['schemas']['RuntimeHealthOut'];

const count = z.number().int().nonnegative();
const runtimeSchema = z.object({
  ready: z.boolean(),
  workers: z.array(
    z.object({
      name: z.string(),
      expected_interval_seconds: z.number().positive(),
      last_cycle: z.string().nullable(),
      last_error_code: z.literal('cycle_failed').nullable(),
      overdue: z.boolean(),
    }),
  ),
  loop_lag_p99_ms: z.number().nonnegative(),
  bus_subscribers: count,
  stream_drops: count,
  bus_queue_depth: count,
  read_rejections: count,
  store_events: count,
  store_bytes: count,
  store_budget_bytes: count,
  rss_bytes: count.nullable(),
  job_queue_depth: count,
  stream_encoder_cached_chars: count,
}) satisfies z.ZodType<RuntimeHealth>;

export const fetchRuntimeHealth = (): Promise<RuntimeHealth> =>
  apiCall('/api/admin/runtime', { schema: runtimeSchema });
