import type { RuleFields } from '@/lib/alertRules';
import type { AreaOfInterest, CollectionPlan } from '@/lib/api/direction';
import type { ReportTemplate } from '@/lib/api/reports';

export function reportPlanProblem(
  planId: string,
  plan: CollectionPlan | undefined,
  aois: readonly AreaOfInterest[] | null,
): string | undefined {
  if (!planId) return undefined;
  const remedy = 'Choose another plan, remove the link, or choose No report.';
  if (!plan || plan.pirs.length === 0)
    return `The linked plan needs an available question. ${remedy}`;
  if (!plan.aoi_id) return undefined;
  if (aois === null) return `The linked area is not loaded. ${remedy}`;
  const area = aois.find((item) => item.id === plan.aoi_id);
  if (
    !area ||
    area.research_area ||
    area.team_id !== plan.team_id ||
    (plan.team_id === null && area.created_by !== plan.created_by)
  )
    return `The linked plan cannot produce an automatic report from this area. ${remedy}`;
  return undefined;
}

/** Use the same prerequisite flags that the report builder publishes. */
export function reportTemplateProblem(
  template: ReportTemplate | undefined,
  fields: RuleFields,
  planProblem: string | undefined,
): string | undefined {
  if (!template) return 'This template is unavailable. Choose another template or No report.';
  if (fields.locationMode === 'shape') return 'Exact-shape alert rules support No report only.';
  if (planProblem) return planProblem;
  const countries = fields.locationMode === 'countries' ? fields.countries : [];
  if (countries.length > 8)
    return 'Reports support up to eight countries. Choose No report or reduce the country set.';
  if (template.needs_country && countries.length !== 1)
    return 'Choose exactly one country, another template, or No report.';
  if (template.needs_question && !fields.planId)
    return 'Link a collection plan with a question, choose another template, or No report.';
  if (template.needs_conflict)
    return 'Alert rules cannot save a tracker conflict. Choose another template or No report.';
  if (template.needs_hazard)
    return 'Alert rules cannot save a tracker hazard. Choose another template or No report.';
  return undefined;
}
