import { z } from 'zod';
import type { components } from './types.gen';

export const bands = [
  'remote_chance',
  'highly_unlikely',
  'unlikely',
  'realistic_possibility',
  'likely',
  'highly_likely',
  'almost_certain',
] as const;
export const confidenceLevels = ['low', 'moderate', 'high'] as const;
export const states = ['open', 'due', 'resolved', 'unresolved', 'superseded'] as const;
const passage = z.object({
  report_version_id: z.string(),
  evidence_id: z.string(),
  passage_id: z.string(),
});
export const forecastVersionSchema = z.object({
  forecast_id: z.string(),
  version_id: z.string(),
  version: z.number().int().positive(),
  claim_id: z.string(),
  claim_version_id: z.string(),
  report_version_id: z.string(),
  issued_at: z.string(),
  horizon_end: z.string(),
  review_at: z.string(),
  criterion: z.object({
    description: z.string(),
    metric_id: z.string().nullable().default(null),
    source_id: z.string().nullable().default(null),
    unit: z.string().nullable().default(null),
    threshold: z.string().nullable().default(null),
    direction: z.enum(['at_least', 'at_most']).nullable().default(null),
    aggregate: z.enum(['minimum', 'maximum']).nullable().default(null),
  }),
  likelihood: z.enum(bands),
  confidence: z.object({
    source_quality: z.enum(confidenceLevels),
    corroboration: z.enum(confidenceLevels),
    coverage: z.enum(confidenceLevels),
    limitation: z.string(),
  }),
  supporting: z.array(passage),
  contrary: z.array(passage),
  supersedes_version_id: z.string().nullable().default(null),
  policy_version: z.string(),
}) satisfies z.ZodType<components['schemas']['ForecastVersion']>;
export const forecastSchema = z.object({
  anchor: z.object({
    id: z.string(),
    kind: z.literal('forecast'),
    report_id: z.string(),
    report_version_id: z.string(),
    claim_id: z.string(),
    claim_revision_id: z.string(),
    owner_id: z.string(),
    team_id: z.string().nullable(),
    created_at: z.string(),
    latest_ordinal: z.number().int(),
  }),
  history: z.object({
    versions: z.array(forecastVersionSchema).min(1).max(64),
    decisions: z.array(
      z.object({
        id: z.string(),
        forecast_version_id: z.string(),
        previous_decision_id: z.string().nullable(),
        recorded_at: z.string(),
        state: z.enum(states),
        method: z.enum(['reviewer', 'clock', 'verified_threshold']),
        actor_id: z.string(),
        reason: z.string(),
        evidence: z.array(passage),
        outcome: z.boolean().nullable().default(null),
        observation: z
          .object({
            metric_id: z.string(),
            source_id: z.string(),
            unit: z.string(),
            aggregate: z.enum(['minimum', 'maximum']),
            value: z.string().nullable(),
            window_start: z.string(),
            window_end: z.string(),
            coverage_verified: z.boolean(),
            verification_reference: z.string().nullable(),
            passage: passage.nullable(),
          })
          .nullable()
          .default(null),
        corrects_decision_id: z.string().nullable().default(null),
        superseding_version_id: z.string().nullable().default(null),
      }),
    ),
  }),
}) satisfies z.ZodType<{
  anchor: components['schemas']['ReportLedgerAnchor'];
  history: components['schemas']['ForecastLedger'];
}>;
export type Forecast = z.infer<typeof forecastSchema>;
export function currentForecast(value: Forecast) {
  const current = value.history.versions.at(-1);
  if (!current) throw new Error('Forecast history has no retained version.');
  return current;
}
export const watchSchema = z.object({
  ledger_id: z.string(),
  report_id: z.string(),
  report_version: z.number().int(),
  title: z.string(),
  version_id: z.string(),
  review_at: z.string(),
  horizon_end: z.string(),
  state: z.enum(states),
  review_due: z.boolean(),
  reminded_at: z.string().nullable(),
  team_id: z.string().nullable(),
});
export const countsSchema = z.object({
  since: z.string(),
  until: z.string(),
  forecast_versions: z.number().int().nonnegative(),
  counting_unit: z.string(),
  caveat: z.string(),
  bands: z.array(
    z.object({
      likelihood: z.enum(bands),
      resolved_true: z.number().int().nonnegative(),
      resolved_false: z.number().int().nonnegative(),
      unresolved: z.number().int().nonnegative(),
      open: z.number().int().nonnegative(),
      due: z.number().int().nonnegative(),
      superseded: z.number().int().nonnegative(),
      resolved_denominator: z.number().int().nonnegative(),
    }),
  ),
}) satisfies z.ZodType<components['schemas']['ForecastCounts']>;
