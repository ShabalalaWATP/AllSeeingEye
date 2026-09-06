/** Run receipts contain server stages only, never research text or estimated percentages. */
import { z } from 'zod';

import { apiCall } from './client';
import type { components } from './types.gen';

export type ResearchRunReceipt = components['schemas']['ResearchRunOut'];
export type ResearchStage = components['schemas']['ResearchStage'];

const receiptSchema: z.ZodType<ResearchRunReceipt> = z.object({
  id: z.uuid(),
  stage: z.enum([
    'planning',
    'collecting',
    'drafting',
    'challenging',
    'validating',
    'saving',
    'completed',
    'cancelled',
    'failed',
    'timed_out',
  ]),
  started_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
  expires_at: z.iso.datetime({ offset: true }),
  report_id: z.uuid().nullable(),
});

export async function readResearchProgress(runId: string, signal: AbortSignal) {
  const id = z.uuid().parse(runId);
  return apiCall(`/api/research/runs/${id}`, { signal, schema: receiptSchema });
}
