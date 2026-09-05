/** LLM profile administration. Keys are sent once and never come back. */
import { z } from 'zod';

import { apiCall, apiSend } from './client';

export const llmRoleSchema = z.enum(['direction', 'assessment', 'devil']);
export type LlmRole = z.infer<typeof llmRoleSchema>;
export const LLM_ROLES: readonly LlmRole[] = llmRoleSchema.options;

export const llmProfileSchema = z.object({
  id: z.string(),
  name: z.string(),
  base_url: z.string(),
  model: z.string(),
  api_key_hint: z.string(),
  roles: z.array(llmRoleSchema),
  max_output_tokens: z.number().int(),
  temperature: z.number(),
  enabled: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type LlmProfile = z.infer<typeof llmProfileSchema>;

export const llmProfilesResponseSchema = z.object({
  items: z.array(llmProfileSchema),
  encryption_available: z.boolean(),
});
export type LlmProfilesResponse = z.infer<typeof llmProfilesResponseSchema>;

export const llmTestSchema = z.object({
  ok: z.boolean(),
  latency_ms: z.number(),
  model: z.string().nullable(),
  error: z.string().nullable(),
});
export type LlmTestResult = z.infer<typeof llmTestSchema>;

export interface LlmProfileInput {
  name: string;
  base_url: string;
  model: string;
  roles: LlmRole[];
  max_output_tokens: number;
  temperature: number;
  enabled: boolean;
  /** Omitted or blank keeps the stored key on update. */
  api_key?: string;
}

export function fetchLlmProfiles(): Promise<LlmProfilesResponse> {
  return apiCall('/api/admin/llm/profiles', { schema: llmProfilesResponseSchema });
}

export function createLlmProfile(input: LlmProfileInput): Promise<LlmProfile> {
  return apiCall('/api/admin/llm/profiles', {
    method: 'POST',
    body: input,
    schema: llmProfileSchema,
  });
}

export function updateLlmProfile(id: string, input: LlmProfileInput): Promise<LlmProfile> {
  return apiCall(`/api/admin/llm/profiles/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: input,
    schema: llmProfileSchema,
  });
}

export function deleteLlmProfile(id: string): Promise<void> {
  return apiSend(`/api/admin/llm/profiles/${encodeURIComponent(id)}`, { method: 'DELETE' });
}

export function testLlmProfile(id: string): Promise<LlmTestResult> {
  return apiCall(`/api/admin/llm/profiles/${encodeURIComponent(id)}/test`, {
    method: 'POST',
    schema: llmTestSchema,
  });
}
