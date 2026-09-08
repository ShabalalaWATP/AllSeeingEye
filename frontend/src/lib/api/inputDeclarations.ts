import { z } from 'zod';
import type { components } from './types.gen';
import { apiCall } from './client';
import { scopedMutation } from '@/lib/workspaceAccess';
import { researchInputReceiptSchema } from './researchInputs';
import { textTransformationSchema, sourceDateSchema } from './sourceProvenance';

export type DeclarationTargets = components['schemas']['InputDeclarationTargetsOut'];
export type InputDeclarations = components['schemas']['InputDeclarationsIn'];
export const declarationTargetsSchema = z.object({
  input_id: z.uuid(),
  sha256: z.string().regex(/^[a-f0-9]{64}$/),
  expires_at: z.iso.datetime({ offset: true }),
  targets: z
    .array(
      z.object({
        event_id: z.string(),
        content_hash: z.string().regex(/^[a-f0-9]{64}$/),
        title: z.string(),
        summary: z.string().nullable(),
        language: z.string(),
        transformations: z.array(textTransformationSchema).default([]),
        source_dates: z.array(sourceDateSchema).default([]),
      }),
    )
    .max(200),
}) satisfies z.ZodType<DeclarationTargets>;
export function fetchDeclarationTargets(inputId: string, signal: AbortSignal) {
  return apiCall(`/api/research/inputs/${encodeURIComponent(inputId)}/declaration-targets`, {
    signal,
    schema: declarationTargetsSchema,
  });
}
export function declareInputProvenance(
  inputId: string,
  body: InputDeclarations,
  signal: AbortSignal,
) {
  return scopedMutation(() =>
    apiCall(`/api/research/inputs/${encodeURIComponent(inputId)}/declarations`, {
      method: 'POST',
      body,
      signal,
      schema: researchInputReceiptSchema,
    }),
  );
}
