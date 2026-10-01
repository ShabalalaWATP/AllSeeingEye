import type { IndicatorRequest, IndicatorUpdateRequest } from '@/lib/alertRules';
import type { Indicator } from '@/lib/api/warning';

/** Every saved value of a rule as a request, so pausing changes nothing but `enabled`. */
export function savedRuleRequest(rule: Indicator): IndicatorRequest {
  return {
    ...(rule.team_id ? { team_id: rule.team_id } : {}),
    ...(rule.plan_id ? { plan_id: rule.plan_id } : {}),
    name: rule.name,
    description: rule.description,
    countries: [...rule.countries],
    ...(rule.bbox?.length === 4 ? { bbox: rule.bbox as [number, number, number, number] } : {}),
    ...(rule.research_area
      ? { research_area: { geometry: { ...rule.research_area.geometry } } }
      : {}),
    categories: [...rule.categories] as IndicatorRequest['categories'] & string[],
    keywords: [...rule.keywords],
    threshold: rule.threshold,
    window_minutes: rule.window_minutes,
    cooldown_minutes: rule.cooldown_minutes,
    severity_floor: rule.severity_floor,
    report_template: rule.report_template,
    enabled: rule.enabled,
  };
}

/**
 * An edit of the revision the person read. Without a request it toggles pause: the rule's
 * saved values go back unchanged apart from `enabled`, so pausing can never widen it.
 */
export function ruleUpdate(
  rule: Indicator,
  request: IndicatorRequest | null,
  confirmWider: boolean,
): IndicatorUpdateRequest {
  const body = request ?? { ...savedRuleRequest(rule), enabled: !rule.enabled };
  return {
    ...body,
    expected_updated_at: rule.updated_at,
    confirm_wider_scope: confirmWider,
  };
}
