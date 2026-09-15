import { z } from 'zod';
import { queryVariantSchema } from '@/lib/api/sourceProvenance';
import type { Report, ReportRequest } from '@/lib/api/reports';
import { categorySchema } from '@/lib/api/eventSchemas';
import { candidateHypothesisSchema, plannedQueryTaskSchema } from '@/lib/api/researchPlan';
import { researchDateError } from './ResearchTimeScope';

export type FollowUpRequest = ReportRequest & { parent_version: number };

const savedArea = z.object({
  geometry: z.record(z.string(), z.unknown()),
  sha256: z.string().regex(/^[0-9a-f]{64}$/),
});

function recordedDateError(since: string, until: string): string | null {
  const start = Date.parse(since);
  const end = Date.parse(until);
  if (!Number.isFinite(start) || !Number.isFinite(end) || start >= end)
    return 'Choose a valid recorded period.';
  if (end - start > 30 * 366 * 86_400_000) return 'The recorded period cannot exceed 30 years.';
  if (end > Date.now() + 5 * 60_000) return 'The recorded period cannot end in the future.';
  return null;
}

const countryCode = z.string().regex(/^[A-Z]{2}$/);
const countryList = z
  .array(countryCode)
  .max(8)
  .refine((codes) => new Set(codes).size === codes.length);

const savedScope = z.object({
  report_language: z
    .enum(['en', 'fr', 'de', 'es', 'ar', 'ru', 'uk', 'zh', 'fa', 'zh-Hans', 'zh-Hant'])
    .optional(),
  report_style: z.enum(['briefing', 'assessment']).optional(),
  country: countryCode.nullable().optional(),
  countries: countryList.optional(),
  country_isos: countryList.optional(),
  categories: z.array(categorySchema).optional(),
  window_hours: z.number().int().nonnegative().optional(),
  research_since: z.iso.datetime({ offset: true }).nullable().optional(),
  research_until: z.iso.datetime({ offset: true }).nullable().optional(),
  research_time_basis: z
    .enum(['publication', 'acquisition_or_publication', 'recorded_time'])
    .optional(),
  research_area: savedArea.nullable().optional(),
  map_origin: z.object({ area: savedArea }).nullable().optional(),
  disclose_area_to_provider: z.boolean().optional(),
  research_web_search: z.boolean().optional(),
  devils_advocacy: z.boolean().optional(),
  hazard: z.string().nullable().optional(),
  conflict: z.string().nullable().optional(),
  plan: z.string().nullable().optional(),
  research_mode: z.enum(['quick', 'detailed', 'advanced']).optional(),
  research_languages: z.array(z.string()).min(1).max(8).optional(),
  research_source_ids: z.array(z.string()).nullable().optional(),
  research_terms: z.array(z.string()).nullable().optional(),
  research_candidate_hypotheses: z.array(candidateHypothesisSchema).max(8).optional(),
  research_planned_tasks: z.array(plannedQueryTaskSchema).max(8).optional(),
  research_query_variants: z.array(queryVariantSchema).optional(),
  research_focus: z.enum(['general', 'company', 'domain', 'document', 'media']).optional(),
  research_subject: z.string().nullable().optional(),
});

/** Reuse explicit saved scope only; unknown or incomplete private scope must never widen. */
export function followUpRequest(parent: Report): FollowUpRequest {
  const scope = savedScope.parse(parent.report.scope);
  if (!Number.isSafeInteger(parent.version.number) || parent.version.number < 1)
    throw new Error('The selected report version is invalid. A follow-up cannot safely start.');
  if (scope.map_origin && scope.research_area)
    throw new Error('The saved area scope is ambiguous. A follow-up cannot safely start.');
  const area = scope.research_area ?? scope.map_origin?.area;
  if (area && scope.research_focus !== 'general')
    throw new Error('This area report type cannot be followed up yet.');
  if (area && scope.disclose_area_to_provider !== true)
    throw new Error('The saved area disclosure is missing. A follow-up cannot safely start.');
  if ((parent.report.scope.map_origin || parent.report.scope.research_area) && !area)
    throw new Error('The exact saved area is unavailable. A follow-up cannot safely start.');
  const countries = scope.countries ?? scope.country_isos ?? (scope.country ? [scope.country] : []);
  if (
    (scope.countries &&
      scope.country_isos &&
      [...scope.countries].sort().join() !== [...scope.country_isos].sort().join()) ||
    (scope.country && (countries.length !== 1 || countries[0] !== scope.country))
  )
    throw new Error('The saved country scope is inconsistent. A follow-up cannot safely start.');
  const fixed = scope.research_since ?? scope.research_until;
  if (scope.research_time_basis === 'recorded_time' && !fixed)
    throw new Error('The recorded-time period is missing. A follow-up cannot safely start.');
  if (area && !fixed)
    throw new Error('The fixed area period is missing. A follow-up cannot safely start.');
  if (fixed) {
    const since = scope.research_since ?? '';
    const until = scope.research_until ?? '';
    const error =
      scope.research_time_basis === 'recorded_time'
        ? recordedDateError(since, until)
        : researchDateError({ since, until });
    if (error) throw new Error(`The saved date scope cannot be preserved: ${error}`);
  } else if (scope.window_hours === 0 || (scope.window_hours ?? 0) > 730 * 24) {
    throw new Error('The saved reporting window is invalid. A follow-up cannot safely start.');
  }
  if (scope.research_web_search && ['document', 'media'].includes(scope.research_focus ?? ''))
    throw new Error('Private attachment scope cannot include public web search.');
  if (
    (parent.report.scope.research_input || parent.report.scope.research_reuse) &&
    !['document', 'media'].includes(scope.research_focus ?? '')
  ) {
    throw new Error(
      'The saved private research scope is incomplete. A follow-up cannot safely start.',
    );
  }
  return {
    disclose_area_to_provider: area ? true : false,
    report_language: scope.report_language ?? 'en',
    report_style: scope.report_style ?? 'assessment',
    country: scope.country ?? null,
    countries,
    research_web_search: scope.research_web_search ?? false,
    categories: scope.categories ?? [],
    hazard: scope.hazard ?? null,
    conflict: scope.conflict ?? null,
    plan: scope.plan ?? null,
    research_subject: scope.research_subject ?? null,
    ...(scope.research_time_basis ? { research_time_basis: scope.research_time_basis } : {}),
    ...(fixed
      ? {
          research_since: scope.research_since ?? null,
          research_until: scope.research_until ?? null,
        }
      : scope.window_hours === undefined
        ? {}
        : { window_hours: scope.window_hours }),
    template: 'ask',
    parent_report_id: parent.report.id,
    parent_version: parent.version.number,
    ...(area ? { research_area: { geometry: area.geometry } } : {}),
    team_id: parent.report.team_id,
    research_focus: scope.research_focus ?? 'general',
    research_mode: scope.research_mode ?? 'quick',
    research_languages: scope.research_languages ?? ['en'],
    ...(scope.research_source_ids === undefined
      ? {}
      : { research_source_ids: scope.research_source_ids }),
    ...(scope.research_terms === undefined ? {} : { research_terms: scope.research_terms }),
    ...(scope.research_candidate_hypotheses === undefined
      ? {}
      : { research_candidate_hypotheses: scope.research_candidate_hypotheses }),
    ...(scope.research_planned_tasks === undefined
      ? {}
      : { research_planned_tasks: scope.research_planned_tasks }),
    ...(scope.research_query_variants === undefined
      ? {}
      : { research_query_variants: scope.research_query_variants }),
    devils_advocacy: scope.devils_advocacy ?? false,
  };
}

export function followUpAvailability(
  parent: Report,
): { request: FollowUpRequest; reason: null } | { request: null; reason: string } {
  try {
    return { request: followUpRequest(parent), reason: null };
  } catch (error) {
    return {
      request: null,
      reason:
        error instanceof Error && error.name !== 'ZodError'
          ? error.message
          : 'The saved scope cannot be safely restored for a follow-up.',
    };
  }
}
