/** LLM profile administration. Keys are sent once and never come back. */
import { z } from 'zod';

import { apiCall, apiSend } from './client';
import type { components } from './types.gen';
import { scopedMutation } from '@/lib/workspaceAccess';

export const llmRoleSchema = z.enum([
  'direction',
  'assessment',
  'devil',
  'translation',
  'embeddings',
]);
export type LlmRole = components['schemas']['LlmRole'];
export const LLM_ROLES: readonly LlmRole[] = llmRoleSchema.options;

export const llmProfileSchema = z.object({
  id: z.string(),
  name: z.string(),
  base_url: z.string(),
  provider: z.enum(['openai_compatible', 'bedrock']),
  model: z.string(),
  api_key_hint: z.string(),
  roles: z.array(llmRoleSchema),
  max_output_tokens: z.number().int(),
  temperature: z.number(),
  enabled: z.boolean(),
  reasoning_effort: z.enum(['none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max']).nullable(),
  revision: z.number().int().positive(),
  tested_at: z.string().nullable(),
  tested_revision: z.number().int().nullable(),
  tested_config_hash: z.string().nullable(),
  is_tested: z.boolean(),
  is_bound: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type LlmProfile = components['schemas']['LlmProfileOut'];

export const llmProfilesResponseSchema = z.object({
  items: z.array(llmProfileSchema),
  encryption_available: z.boolean(),
});
export type LlmProfilesResponse = components['schemas']['LlmProfilesOut'];

export const llmTestSchema = z.object({
  ok: z.boolean(),
  latency_ms: z.number(),
  model: z.string().nullable(),
  error: z.string().nullable(),
  revision: z.number().int().nullable(),
  tested_at: z.string().nullable(),
  tested_config_hash: z.string().nullable(),
});
export type LlmTestResult = components['schemas']['LlmTestOut'];

export type LlmProfileInput = components['schemas']['LlmProfileIn'];
export type LlmConnection = components['schemas']['LlmConnectionOut'];
export type LlmConnectionInput = components['schemas']['LlmConnectionIn'];

export const connectionSchema = z.object({
  team_id: z.uuid().nullable(),
  user_id: z.uuid().nullable().default(null),
  profile_id: z.uuid(),
  profile_revision: z.number().int(),
  tested_config_hash: z.string(),
  activated_at: z.string(),
  activated_by: z.uuid(),
  revision: z.number().int(),
});
const connectionsSchema = z.object({ items: z.array(connectionSchema) });
const modelsSchema = z.object({ models: z.array(z.string().max(120)).max(1000) });

export function fetchLlmConnections(): Promise<{ items: LlmConnection[] }> {
  return apiCall('/api/admin/llm/connections', { schema: connectionsSchema });
}
export function fetchLlmModels(
  id: string,
  signal?: AbortSignal,
): Promise<components['schemas']['LlmModelsOut']> {
  return scopedMutation(() =>
    apiCall(`/api/admin/llm/profiles/${encodeURIComponent(id)}/models`, {
      schema: modelsSchema,
      ...(signal ? { signal } : {}),
    }),
  );
}
export function applyLlmConnection(
  body: LlmConnectionInput,
  signal?: AbortSignal,
): Promise<LlmConnection> {
  return scopedMutation(() =>
    apiCall('/api/admin/llm/connections', {
      method: 'PUT',
      body,
      schema: connectionSchema,
      ...(signal ? { signal } : {}),
    }),
  );
}
export function resetTeamLlmConnection(
  teamId: string,
  revision: number,
  signal?: AbortSignal,
): Promise<void> {
  return scopedMutation(() =>
    apiSend(
      `/api/admin/llm/connections/team/${encodeURIComponent(teamId)}?expected_revision=${revision}`,
      { method: 'DELETE', ...(signal ? { signal } : {}) },
    ),
  );
}

export function fetchLlmProfiles(): Promise<LlmProfilesResponse> {
  return apiCall('/api/admin/llm/profiles', { schema: llmProfilesResponseSchema });
}

export function createLlmProfile(
  input: LlmProfileInput,
  signal?: AbortSignal,
): Promise<LlmProfile> {
  return scopedMutation(() =>
    apiCall('/api/admin/llm/profiles', {
      method: 'POST',
      body: input,
      schema: llmProfileSchema,
      ...(signal ? { signal } : {}),
    }),
  );
}

export function updateLlmProfile(
  id: string,
  input: LlmProfileInput,
  signal?: AbortSignal,
): Promise<LlmProfile> {
  return scopedMutation(() =>
    apiCall(`/api/admin/llm/profiles/${encodeURIComponent(id)}`, {
      method: 'PUT',
      body: input,
      schema: llmProfileSchema,
      ...(signal ? { signal } : {}),
    }),
  );
}

export function deleteLlmProfile(id: string, signal?: AbortSignal): Promise<void> {
  return scopedMutation(() =>
    apiSend(`/api/admin/llm/profiles/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      ...(signal ? { signal } : {}),
    }),
  );
}

export function testLlmProfile(id: string, signal?: AbortSignal): Promise<LlmTestResult> {
  return scopedMutation(() =>
    apiCall(`/api/admin/llm/profiles/${encodeURIComponent(id)}/test`, {
      method: 'POST',
      schema: llmTestSchema,
      ...(signal ? { signal } : {}),
    }),
  );
}

export function discoverLlmModels(
  body: { provider: 'openai_compatible'; base_url: string; api_key?: string; profile_id?: string },
  signal: AbortSignal,
) {
  return apiCall('/api/admin/llm/models/discover', {
    method: 'POST',
    body,
    signal,
    schema: modelsSchema,
  });
}
export function resetUserLlmConnection(userId: string, revision: number, signal?: AbortSignal) {
  return scopedMutation(() =>
    apiSend(
      `/api/admin/llm/connections/user/${encodeURIComponent(userId)}?expected_revision=${revision}`,
      { method: 'DELETE', ...(signal ? { signal } : {}) },
    ),
  );
}
