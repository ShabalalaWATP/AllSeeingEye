/** Human verdicts on whether a model citation supports its saved judgement (KAN-114). */
import { z } from 'zod';

import { scopedMutation } from '@/lib/workspaceAccess';

import { apiCall, apiFile } from './client';
import type { components } from './types.gen';

export type CitationVerdict = components['schemas']['CitationVerdictOut'];
export type CitationVerdictList = components['schemas']['CitationVerdictListOut'];
export type CitationVerdictValue = components['schemas']['CitationVerdictValue'];
export type CitationVerdictInput = components['schemas']['CitationVerdictIn'];

export const VERDICT_VALUES = [
  'supports',
  'partly_supports',
  'does_not_support',
  'cannot_tell',
] as const satisfies readonly CitationVerdictValue[];

export const VERDICT_LABELS: Record<CitationVerdictValue, string> = {
  supports: 'Supports',
  partly_supports: 'Partly supports',
  does_not_support: 'Does not support',
  cannot_tell: 'Cannot tell',
};

/** Count lines for aggregate views: each verdict out of the current verdicts, never a score. */
export function verdictShares(
  counts: Record<CitationVerdictValue, number>,
  current: number,
): string[] {
  const format = new Intl.NumberFormat('en-GB');
  const noun = current === 1 ? 'current verdict' : 'current verdicts';
  return VERDICT_VALUES.map(
    (value) =>
      `${VERDICT_LABELS[value]}: ${format.format(counts[value])} of ${format.format(current)} ${noun}`,
  );
}

const verdictSchema = z.object({
  id: z.uuid(),
  report_id: z.uuid(),
  report_version_id: z.uuid(),
  version_number: z.number().int().positive(),
  judgement_id: z.string().min(1).max(200),
  label: z.string().min(1).max(200),
  relation: z.enum(['supporting', 'contradicting']),
  verdict: z.enum(VERDICT_VALUES),
  note: z.string().max(300).nullable(),
  reviewer_id: z.uuid(),
  team_id: z.uuid().nullable(),
  recorded_at: z.string(),
}) satisfies z.ZodType<CitationVerdict>;

const listSchema = z.object({
  verdicts: z.array(verdictSchema),
  can_record: z.boolean(),
  limit: z.number().int().positive(),
  note_limit: z.number().int().positive(),
  notice: z.string().max(500),
}) satisfies z.ZodType<CitationVerdictList>;

function path(reportId: string, version: number) {
  return `/api/reports/${encodeURIComponent(reportId)}/versions/${String(version)}/citation-verdicts`;
}

export function fetchCitationVerdicts(
  reportId: string,
  version: number,
): Promise<CitationVerdictList> {
  return apiCall(path(reportId, version), { schema: listSchema });
}

export function recordCitationVerdict(
  reportId: string,
  version: number,
  body: CitationVerdictInput,
): Promise<CitationVerdict> {
  return scopedMutation(() =>
    apiCall(path(reportId, version), { method: 'POST', body, schema: verdictSchema }),
  );
}

export function fetchCitationVerdictExport(reportId: string, version: number) {
  return apiFile(`${path(reportId, version)}/export`, {
    headers: { Accept: 'application/x-ndjson' },
  });
}
