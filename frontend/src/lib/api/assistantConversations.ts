import { z } from 'zod';
import { apiCall, apiSend } from './client';
import { assistantAnswerSchema, assistantSourceCategorySchema } from './assistant';
import type { components } from './types.gen';

export type AssistantConversation = components['schemas']['SavedConversationOut'];
export type AssistantConversationSummary = components['schemas']['SavedConversationSummaryOut'];
export type AssistantConversationTurn = components['schemas']['SavedTurnOut'];
export type AssistantConversationPayload = components['schemas']['SavedConversationIn'];

const turnSchema: z.ZodType<AssistantConversationTurn> = z
  .object({
    question: z.string().min(1).max(2000),
    scope: z.enum(['global', 'viewport', 'selected', 'report']),
    time_window: z.enum(['auto', '48', '120', '168', '336', '720', '2160', '8760']),
    source_categories: z.array(assistantSourceCategorySchema).max(14).nullable(),
    report: z
      .object({ id: z.uuid(), version: z.number().int().positive() })
      .nullable()
      .default(null),
    answer: assistantAnswerSchema,
  })
  .superRefine((turn, context) => {
    const answerReport = turn.answer.report;
    if (turn.scope === 'report') {
      if (
        turn.report == null ||
        answerReport == null ||
        turn.answer.scope.mode !== 'report' ||
        turn.report.id !== answerReport.id ||
        turn.report.version !== answerReport.version
      ) {
        context.addIssue({
          code: 'custom',
          message: 'Report-scoped saved turns must identify the exact report edition.',
        });
      }
    } else if (turn.report != null || turn.answer.scope.mode === 'report' || answerReport != null) {
      context.addIssue({
        code: 'custom',
        message: 'Map-scoped saved turns cannot include report context.',
      });
    }
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
