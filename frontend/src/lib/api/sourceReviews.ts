/** Analyst source reviews and reviewed-assessment snapshots for exact report versions. */
import { z } from 'zod';

import { scopedMutation } from '@/lib/workspaceAccess';

import { apiCall } from './client';
import type { components } from './types.gen';

export type SourceReviewKind = components['schemas']['SourceReviewKind'];
export type SourceReviewInput = components['schemas']['SourceReviewIn'];
export type SourceReviewRevision = components['schemas']['SourceReviewRevision'];
export type SourceSnapshotSummary = components['schemas']['SourceSnapshotSummaryOut'];
export type SourceSnapshotList = components['schemas']['SourceSnapshotListOut'];
export type Reliability = components['schemas']['Reliability'];
export type Credibility = components['schemas']['Credibility'];
export type Authenticity = components['schemas']['Authenticity'];

/** The retained revision limit for one review history; the server enforces it too. */
export const MAX_REVIEW_REVISIONS = 100;

export const RELIABILITY_LABELS: Record<Reliability, string> = {
  A: 'A: completely reliable',
  B: 'B: usually reliable',
  C: 'C: fairly reliable',
  D: 'D: not usually reliable',
  E: 'E: unreliable',
  F: 'F: reliability cannot be judged',
};
export const CREDIBILITY_LABELS: Record<Credibility, string> = {
  1: '1: confirmed by other sources',
  2: '2: probably true',
  3: '3: possibly true',
  4: '4: doubtful',
  5: '5: improbable',
  6: '6: truth cannot be judged',
};
export const AUTHENTICITY_LABELS: Record<Authenticity, string> = {
  established: 'Established',
  unassessed: 'Unassessed',
  disputed: 'Disputed',
};

const reliability = z.enum(['A', 'B', 'C', 'D', 'E', 'F']);
const credibility = z.union(
  [1, 2, 3, 4, 5, 6].map((value) => z.literal(value)),
) as z.ZodType<Credibility>;
const authenticity = z.enum(['established', 'unassessed', 'disputed']);
const text = z.string().max(1000);

const revisionSchema = z.object({
  scope: z.object({ owner_id: z.uuid(), team_id: z.uuid().nullable() }),
  target: z.object({
    report_id: z.uuid(),
    report_version_id: z.uuid(),
    source_id: z.string().max(200),
    subject: z.string().max(200),
    capture_id: z.string().max(200),
    claim_id: z.string().max(200),
  }),
  kind: z.enum(['reliability', 'credibility', 'authenticity']),
  number: z.number().int().min(1).max(MAX_REVIEW_REVISIONS),
  review: z.object({
    id: z.uuid(),
    assessor: z.enum(['reviewer', 'policy', 'model', 'third_party', 'legacy']),
    assessor_id: z.uuid(),
    status: z.enum(['applied', 'proposal']),
    basis: text,
    policy_version: z.string().max(200),
    recorded_at: z.string(),
    reviewed_at: z.string().nullable().default(null),
    supersedes: z.uuid().nullable().default(null),
    policy_note: text.nullable().default(null),
  }),
  reliability: reliability.nullable().default(null),
  expertise_basis: text.nullable().default(null),
  credibility: credibility.nullable().default(null),
  authenticity: z
    .object({
      evidence_id: z.string().max(200),
      issuer_id: z.string().max(200),
      status: authenticity,
      basis: text,
      observed_reference: z.string().max(400).nullable().default(null),
    })
    .nullable()
    .default(null),
}) satisfies z.ZodType<SourceReviewRevision>;

const summarySchema = z.object({
  id: z.uuid(),
  report_id: z.uuid(),
  report_version_id: z.uuid(),
  authored_by: z.uuid(),
  created_at: z.string(),
  decisions: z.number().int().nonnegative(),
  subjects: z.record(z.string(), z.string().max(200)),
}) satisfies z.ZodType<SourceSnapshotSummary>;

const listSchema = z.object({
  snapshots: z.array(summarySchema).max(20),
  limit: z.number().int().positive(),
}) satisfies z.ZodType<SourceSnapshotList>;

/** Only the reviewed fields the reader shows; the frozen projection stays on the server. */
const snapshotSchema = z.object({
  id: z.uuid(),
  report_version_id: z.uuid(),
  authored_by: z.uuid(),
  created_at: z.string(),
  projection: z.object({
    evidence: z.array(z.object({ capture_id: z.string(), label: z.string() })),
    claims: z.array(z.object({ claim_id: z.string(), judgement_id: z.string() })),
    assessments: z.array(
      z.object({
        evidence_id: z.string(),
        claim_id: z.string(),
        source_id: z.string(),
        subject: z.string(),
        reliability,
        credibility,
        source_revision: z.object({ review: z.object({ id: z.uuid() }) }).nullable(),
        assertion_revision: z.object({ review: z.object({ id: z.uuid() }) }).nullable(),
        authenticity: z.object({ status: authenticity }).nullable(),
      }),
    ),
  }),
});
export type ReviewedSnapshot = z.infer<typeof snapshotSchema>;

export interface ReviewTarget {
  label: string;
  judgement_id: string;
  subject: string;
  kind: SourceReviewKind;
}

function base(reportId: string, version: number) {
  return `/api/reports/${encodeURIComponent(reportId)}/versions/${String(version)}`;
}

export function fetchSourceReviewHistory(
  reportId: string,
  version: number,
  target: ReviewTarget,
): Promise<SourceReviewRevision[]> {
  const query = new URLSearchParams({ ...target });
  return apiCall(`${base(reportId, version)}/source-reviews?${query.toString()}`, {
    schema: z.array(revisionSchema).max(MAX_REVIEW_REVISIONS),
  });
}

export function recordSourceReview(reportId: string, version: number, body: SourceReviewInput) {
  return scopedMutation(() =>
    apiCall(`${base(reportId, version)}/source-reviews`, {
      method: 'POST',
      body,
      schema: revisionSchema,
    }),
  );
}

export function fetchSourceSnapshots(reportId: string, version: number) {
  return apiCall(`${base(reportId, version)}/source-assessment-snapshots`, {
    schema: listSchema,
  });
}

export function createSourceSnapshot(
  reportId: string,
  version: number,
  subjects: Record<string, string>,
) {
  return scopedMutation(() =>
    apiCall(`${base(reportId, version)}/source-assessment-snapshots`, {
      method: 'POST',
      body: { subjects },
      schema: snapshotSchema,
    }),
  );
}

export function fetchSourceSnapshot(reportId: string, version: number, snapshotId: string) {
  return apiCall(
    `${base(reportId, version)}/source-assessment-snapshots/${encodeURIComponent(snapshotId)}`,
    { schema: snapshotSchema },
  );
}
