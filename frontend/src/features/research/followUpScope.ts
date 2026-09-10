import { z } from 'zod';
import { queryVariantSchema } from '@/lib/api/sourceProvenance';
import type { Report, ReportRequest } from '@/lib/api/reports';
import { categorySchema } from '@/lib/api/eventSchemas';
import { candidateHypothesisSchema, plannedQueryTaskSchema } from '@/lib/api/researchPlan';

const savedScope = z.object({
  report_language: z
    .enum(['en', 'fr', 'de', 'es', 'ar', 'ru', 'uk', 'zh', 'fa', 'zh-Hans', 'zh-Hant'])
    .optional(),
  report_style: z.enum(['briefing', 'assessment']).optional(),
  country: z.string().nullable().optional(),
  categories: z.array(categorySchema).optional(),
  window_hours: z.number().int().positive().optional(),
  devils_advocacy: z.boolean().optional(),
  hazard: z.string().nullable().optional(),
  conflict: z.string().nullable().optional(),
  plan: z.string().nullable().optional(),
  research_mode: z.enum(['quick', 'detailed']).optional(),
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
export function followUpRequest(parent: Report): ReportRequest {
  if (parent.report.scope.research_time_basis === 'recorded_time') {
    throw new Error(
      'Start a new historical request. Ordinary follow-ups cannot preserve this time policy.',
    );
  }
  if (parent.report.scope.map_origin || parent.report.scope.research_area) {
    throw new Error(
      'Start area research from its saved map revision. Ordinary follow-ups cannot preserve that scope.',
    );
  }
  const scope = savedScope.parse(parent.report.scope);
  if (
    (parent.report.scope.research_input || parent.report.scope.research_reuse) &&
    !['document', 'media'].includes(scope.research_focus ?? '')
  ) {
    throw new Error(
      'The saved private research scope is incomplete. A follow-up cannot safely start.',
    );
  }
  return {
    disclose_area_to_provider: false,
    report_language: scope.report_language ?? 'en',
    report_style: scope.report_style ?? 'assessment',
    country: scope.country ?? null,
    categories: scope.categories ?? [],
    hazard: scope.hazard ?? null,
    conflict: scope.conflict ?? null,
    plan: scope.plan ?? null,
    research_subject: scope.research_subject ?? null,
    ...(scope.window_hours === undefined ? {} : { window_hours: scope.window_hours }),
    template: 'ask',
    parent_report_id: parent.report.id,
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
