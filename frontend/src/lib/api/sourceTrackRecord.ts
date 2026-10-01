import { z } from 'zod';

import { apiCall } from './client';
import type { components } from './types.gen';

const savedStatus = z.enum(['ready', 'needs_review', 'failed']);

const statusesSchema = z.object({
  ready: z.number().int().nonnegative(),
  needs_review: z.number().int().nonnegative(),
  failed: z.number().int().nonnegative(),
}) satisfies z.ZodType<components['schemas']['TrackRecordStatusesOut']>;

const valueSchema = z.object({
  value: z.string().max(40),
  items: z.number().int().nonnegative(),
}) satisfies z.ZodType<components['schemas']['TrackRecordValueOut']>;

export const sourceTrackRecordSchema = z.object({
  source_id: z.string().max(120),
  report_bound: z.number().int().positive(),
  reports_considered: z.number().int().nonnegative(),
  visible_reports: z.number().int().nonnegative(),
  reports_citing: z.number().int().nonnegative(),
  frozen_items: z.number().int().nonnegative(),
  roles: z.object({
    supporting_judgements: z.number().int().nonnegative(),
    contradicting_judgements: z.number().int().nonnegative(),
    items_cited_elsewhere: z.number().int().nonnegative(),
    items_not_cited: z.number().int().nonnegative(),
  }),
  reports_by_status: statusesSchema,
  judgements_by_status: statusesSchema,
  reliability: z.array(valueSchema),
  credibility: z.array(valueSchema),
  entries: z.array(
    z.object({
      report_id: z.uuid(),
      title: z.string().max(300),
      version_number: z.number().int().positive(),
      status: savedStatus,
      saved_at: z.string(),
      items: z.number().int().nonnegative(),
      supporting_judgements: z.number().int().nonnegative(),
      contradicting_judgements: z.number().int().nonnegative(),
      grades: z.array(z.string().max(40)),
    }),
  ),
  entries_total: z.number().int().nonnegative(),
  reviews: z.array(
    z.object({
      kind: z.enum(['reliability', 'credibility', 'authenticity']),
      decision: z.string().max(40),
      recorded_at: z.string(),
      report_id: z.uuid(),
      team_scoped: z.boolean(),
    }),
  ),
  reviews_total: z.number().int().nonnegative(),
  citation_verdicts: z.object({
    available: z.boolean(),
    note: z.string().max(500),
    citations: z.number().int().nonnegative(),
    citations_with_verdicts: z.number().int().nonnegative(),
    current_verdicts: z.number().int().nonnegative(),
    superseded_verdicts: z.number().int().nonnegative(),
    supports: z.number().int().nonnegative(),
    partly_supports: z.number().int().nonnegative(),
    does_not_support: z.number().int().nonnegative(),
    cannot_tell: z.number().int().nonnegative(),
    reviewers: z.number().int().nonnegative(),
  }),
}) satisfies z.ZodType<components['schemas']['SourceTrackRecordOut']>;

export type SourceTrackRecord = components['schemas']['SourceTrackRecordOut'];

/** Counts from the caller's latest visible saved reports, computed on request. */
export function fetchSourceTrackRecord(sourceId: string): Promise<SourceTrackRecord> {
  return apiCall(`/api/sources/${encodeURIComponent(sourceId)}/track-record`, {
    schema: sourceTrackRecordSchema,
  });
}
