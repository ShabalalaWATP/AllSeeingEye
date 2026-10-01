import type { RuleFields } from '@/lib/alertRules';
import { emptyRuleFields, ruleFieldsFromIndicator, splitKeywords } from '@/lib/alertRules';
import type { ReportWatchDraft } from '@/lib/alertRuleDraft';
import type { Indicator } from '@/lib/api/warning';

import type { RuleFormMode } from './IndicatorForm';

/** A report draft's starting values: its wording, places and categories, all editable. */
function fromReport(draft: ReportWatchDraft): RuleFields {
  const { source } = draft;
  return {
    ...emptyRuleFields(),
    name: `Watch: ${source.title}`,
    description: `From “${source.title}”, version ${String(source.version)}, judgement ${String(source.judgementNumber)}. Watch for: ${draft.indicators.join('; ')}`,
    locationMode: draft.countries.length > 0 ? 'countries' : draft.geometry ? 'shape' : 'countries',
    countries: [...draft.countries],
    categoryMode: draft.categories.length > 0 ? 'specific' : 'all',
    categories: [...draft.categories],
    keywords: draft.indicators.join(', '),
  };
}

export function initialRuleFields(mode: RuleFormMode): RuleFields {
  if (mode.kind === 'edit') return ruleFieldsFromIndicator(mode.rule);
  if (mode.reportDraft) return fromReport(mode.reportDraft);
  if (mode.areaDraft)
    return { ...emptyRuleFields(), locationMode: mode.areaDraft.geometry ? 'shape' : 'area' };
  return emptyRuleFields();
}

/** Restrictions an edit removes entirely; each needs an explicit confirmation to save. */
export function widenedLabels(rule: Indicator, fields: RuleFields): string[] {
  const widened: string[] = [];
  const located = rule.countries.length > 0 || rule.bbox !== null || Boolean(rule.research_area);
  if (located && fields.locationMode === 'worldwide') widened.push('location');
  if (rule.categories.length > 0 && fields.categoryMode === 'all') widened.push('category');
  if (rule.keywords.length > 0 && splitKeywords(fields.keywords).length === 0)
    widened.push('keyword');
  return widened;
}
