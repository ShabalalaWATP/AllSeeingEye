import { http, HttpResponse } from 'msw';

import type { RuntimeHealth } from '@/lib/api/runtime';

export const runtimeHealth: RuntimeHealth = {
  ready: true,
  workers: [
    {
      name: 'scheduler',
      expected_interval_seconds: 60,
      last_cycle: '2026-09-30T10:00:00Z',
      last_error_code: null,
      overdue: false,
    },
  ],
  loop_lag_p99_ms: 2,
  bus_subscribers: 3,
  stream_drops: 7,
  bus_queue_depth: 0,
  read_rejections: 0,
  store_events: 10,
  store_bytes: 1024,
  store_budget_bytes: 1024 * 1024,
  rss_bytes: null,
  job_queue_depth: 2,
  stream_encoder_cached_chars: 200,
};

export const runtimeHandlers = [
  http.get('/api/admin/runtime', () => HttpResponse.json(runtimeHealth)),
];
