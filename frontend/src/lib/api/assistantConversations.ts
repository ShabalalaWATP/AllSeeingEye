import { z } from 'zod';
import { apiCall, apiSend } from './client';
import { assistantAnswerSchema, assistantSourceCategorySchema } from './assistant';
import type { components } from './types.gen';

export type AssistantConversation = components['schemas']['SavedConversationOut'];
export type AssistantConversationSummary = components['schemas']['SavedConversationSummaryOut'];
export type AssistantConversationTurn = components['schemas']['SavedTurnOut'];
export type AssistantConversationPayload = components['schemas']['SavedConversationIn'];

const turnSchema: z.ZodType<AssistantConversationTurn> = z.object({
  question: z.string().min(1).max(2000),
  scope: z.enum(['global', 'viewport', 'selected']),
  time_window: z.enum(['auto', '48', '120', '168', '336', '720', '2160', '8760']),
  source_categories: z.array(assistantSourceCategorySchema).max(14).nullable(),
  answer: assistantAnswerSchema,
});
const summarySchema = z.object({
  id: z.uuid(),
  title: z.string(),
  turn_count: z.number().int().min(1).max(8),
  created_at: z.string(),
  updated_at: z.string(),
});
const conversationSchema: z.ZodType<AssistantConversation> = summarySchema
  .omit({ turn_count: true })
  .extend({
    turns: z.array(turnSchema).min(1).max(8),
    snapshot_notice: z.string(),
  });
const pageSchema = z.object({ items: z.array(summarySchema).max(30) });
const base = '/api/assistant/conversations';
const path = (id: string) => `${base}/${encodeURIComponent(id)}`;

export function listAssistantConversations(signal?: AbortSignal) {
  return apiCall(base, { schema: pageSchema, ...(signal ? { signal } : {}) });
}
export function getAssistantConversation(id: string, signal?: AbortSignal) {
  return apiCall(path(id), { schema: conversationSchema, ...(signal ? { signal } : {}) });
}
export function createAssistantConversation(
  body: AssistantConversationPayload,
  signal?: AbortSignal,
) {
  return apiCall(base, {
    method: 'POST',
    body,
    schema: conversationSchema,
    ...(signal ? { signal } : {}),
    retryAfterRefresh: false,
  });
}
export function updateAssistantConversation(
  id: string,
  body: AssistantConversationPayload,
  signal?: AbortSignal,
) {
  return apiCall(path(id), {
    method: 'PUT',
    body,
    schema: conversationSchema,
    ...(signal ? { signal } : {}),
    retryAfterRefresh: false,
  });
}
export function deleteAssistantConversation(id: string, signal?: AbortSignal) {
  return apiSend(path(id), {
    method: 'DELETE',
    ...(signal ? { signal } : {}),
    retryAfterRefresh: false,
  });
}
