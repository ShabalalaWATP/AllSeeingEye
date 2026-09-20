import { z } from 'zod';

import { scopedMutation } from '@/lib/workspaceAccess';
import { apiCall } from './client';
import { ApiError } from './errors';
import { reportJobSchema } from './reportJobs';
import {
  briefDraftSchema,
  briefSummarySchema,
  researchBriefSchema,
  type BriefDraft,
  type ResearchBrief,
} from './researchBriefSchema';

const briefResponse = z.object({ brief: researchBriefSchema });
const briefPage = z.object({
  items: z.array(briefSummarySchema),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
});

export const BRIEF_PAGE_SIZE = 50;

export async function fetchBriefs(signal: AbortSignal, offset = 0) {
  return apiCall(`/api/research/briefs?limit=${BRIEF_PAGE_SIZE}&offset=${offset}`, {
    schema: briefPage,
    signal,
  });
}

export async function fetchBrief(id: string, revision: number | undefined, signal: AbortSignal) {
  const base = `/api/research/briefs/${encodeURIComponent(id)}`;
  const path = revision === undefined ? base : `${base}/revisions/${String(revision)}`;
  const response = await apiCall(path, { schema: briefResponse, signal });
  if (
    response.brief.identity.id !== id ||
    (revision !== undefined && response.brief.identity.revision !== revision)
  )
    throw new ApiError(
      502,
      'invalid_response',
      'The server returned a different Research Brief revision.',
    );
  return response.brief;
}

export function createBrief(draft: BriefDraft, signal: AbortSignal): Promise<ResearchBrief> {
  const body = briefDraftSchema.parse(draft);
  return scopedMutation(
    async () =>
      (
        await apiCall('/api/research/briefs', {
          method: 'POST',
          body,
          schema: briefResponse,
          signal,
          retryAfterRefresh: false,
        })
      ).brief,
  );
}

export async function reviseBrief(brief: ResearchBrief, draft: BriefDraft, signal: AbortSignal) {
  const body = { ...briefDraftSchema.parse(draft), base_revision: brief.identity.revision };
  const result = await scopedMutation(
    async () =>
      (
        await apiCall(`/api/research/briefs/${encodeURIComponent(brief.identity.id)}/revisions`, {
          method: 'POST',
          body,
          schema: briefResponse,
          signal,
          retryAfterRefresh: false,
        })
      ).brief,
  );
  if (
    result.identity.id !== brief.identity.id ||
    result.identity.revision !== brief.identity.revision + 1
  )
    throw new ApiError(
      502,
      'invalid_response',
      'The server returned a different Research Brief revision.',
    );
  return result;
}

export function runBrief(brief: ResearchBrief, signal: AbortSignal, requestId: string) {
  return scopedMutation(() =>
    apiCall('/api/report-jobs/from-brief', {
      method: 'POST',
      body: {
        request_id: requestId,
        brief_id: brief.identity.id,
        revision: brief.identity.revision,
      },
      schema: reportJobSchema,
      signal,
      retryAfterRefresh: false,
    }),
  );
}
