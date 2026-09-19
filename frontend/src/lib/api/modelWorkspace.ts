/** One transaction updates the shared assignment and allowance records. */
import { z } from 'zod';
import { apiCall } from './client';
import { connectionSchema } from './llm';
import { policySchema } from './aiUsage';
import type { components } from './types.gen';
import { scopedMutation } from '@/lib/workspaceAccess';

export type ModelWorkspaceInput = components['schemas']['LlmWorkspaceIn'];
export type ModelWorkspaceResult = components['schemas']['LlmWorkspaceOut'];
const resultSchema = z.object({
  connections: z.array(connectionSchema),
  policies: z.array(policySchema),
});

export function saveModelWorkspace(body: ModelWorkspaceInput, signal: AbortSignal) {
  return scopedMutation(() =>
    apiCall('/api/admin/llm/workspace', {
      method: 'PUT',
      body,
      signal,
      schema: resultSchema,
    }),
  );
}
