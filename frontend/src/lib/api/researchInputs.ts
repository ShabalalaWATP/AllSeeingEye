/** Authenticated transient imports. Their response types come from the generated API contract. */
import { z } from 'zod';

import { scopedMutation } from '@/lib/workspaceAccess';

import { apiCall } from './client';
import type { components } from './types.gen';

export type ResearchInputReceipt = components['schemas']['ResearchInputOut'];

const hash = z.string().regex(/^[a-f0-9]{64}$/);
const previewSchema = z.object({
  seconds: z.number().min(0).max(600),
  sha256: hash,
  png_base64: z
    .string()
    .max(1_398_104)
    .regex(/^iVBORw0KGgo[A-Za-z0-9+/]*={0,2}$/),
});

const receiptSchema: z.ZodType<ResearchInputReceipt> = z.object({
  id: z.uuid(),
  filename: z.string().max(120),
  media_type: z.string().max(120),
  sha256: hash,
  imported_at: z.iso.datetime({ offset: true }),
  expires_at: z.iso.datetime({ offset: true }),
  event_count: z.number().int().min(1).max(200),
  extracted_characters: z.number().int().min(0).max(200_000),
  preview: z.string().max(1000),
  limitations: z.array(z.string().max(500)).max(20),
  previews: z.array(previewSchema).max(3).default([]),
});

export function uploadResearchInput(
  file: File,
  signal: AbortSignal,
): Promise<ResearchInputReceipt> {
  return scopedMutation(() =>
    apiCall(`/api/research/inputs?filename=${encodeURIComponent(file.name)}`, {
      method: 'POST',
      rawBody: file,
      signal,
      schema: receiptSchema,
    }),
  );
}
