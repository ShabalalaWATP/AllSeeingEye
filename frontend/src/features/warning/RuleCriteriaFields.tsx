import { CategoryChoice } from '@/components/ui/CategoryChoice';
import { SelectField, TextField } from '@/components/ui/Field';
import type { RuleFields } from '@/lib/alertRules';
import {
  COOLDOWN_RANGE,
  MAX_KEYWORD_LENGTH,
  MAX_KEYWORDS,
  WINDOWS,
  windowLabel,
} from '@/lib/alertRules';
import type { FieldErrorState } from '@/lib/api/fieldErrors';
import type { ReportTemplate } from '@/lib/api/reports';
import { reportTemplateProblem } from './reportTemplates';

export type RuleFieldKey =
  | 'team_id'
  | 'plan_id'
  | 'area'
  | 'name'
  | 'description'
  | 'categories'
  | 'keywords'
  | 'threshold'
  | 'baseline_ratio'
  | 'baseline_days'
  | 'window_minutes'
  | 'cooldown_minutes'
  | 'severity_floor'
  | 'report_template';

/** What to count, how many, over what time, and what happens when the rule fires. */
export function RuleCriteriaFields({
  fields,
  change,
  errors,
  templates,
  planProblem,
}: {
  fields: RuleFields;
  change: (patch: Partial<RuleFields>) => void;
  errors: FieldErrorState<RuleFieldKey>;
  templates: readonly ReportTemplate[];
  planProblem: string | undefined;
}) {
  const shape = fields.locationMode === 'shape';
  const available = templates.filter(
    (template) => !reportTemplateProblem(template, fields, planProblem),
  );
  const problem = fields.template
    ? reportTemplateProblem(
        templates.find((template) => template.id === fields.template),
        fields,
        planProblem,
      )
    : undefined;
  const windows = WINDOWS.some((option) => option.value === fields.window)
    ? WINDOWS
    : [
        ...WINDOWS,
        { value: fields.window, label: `${windowLabel(Number(fields.window))} (saved)` },
      ];
  return (
    <>
      <CategoryChoice
        id={errors.id('categories')}
        all={fields.categoryMode === 'all'}
        value={fields.categories}
        onAllChange={(all) => change({ categoryMode: all ? 'all' : 'specific' })}
        onChange={(categories) => change({ categories })}
        error={errors.message('categories')}
      />
      <div className="grid gap-3 md:grid-cols-3">
        <TextField
          label="Keywords"
          {...errors.field('keywords')}
          hint={`Optional. Matches if any word or phrase appears literally in an item's title or summary, ignoring case. Comma separated, up to ${String(MAX_KEYWORDS)}, each up to ${String(MAX_KEYWORD_LENGTH)} characters.`}
          value={fields.keywords}
          onChange={(event) => change({ keywords: event.target.value })}
        />
        <TextField
          label="Threshold"
          {...errors.field('threshold')}
          hint="Fires at this many matching items in the window."
          type="number"
          min={1}
          max={10000}
          value={fields.threshold}
          onChange={(event) => change({ threshold: event.target.value })}
        />
        <SelectField
          label="Window"
          {...errors.field('window_minutes')}
          hint="How far back matching items are counted."
          value={fields.ratio ? '60' : fields.window}
          disabled={Boolean(fields.ratio)}
          onChange={(event) => change({ window: event.target.value })}
          options={windows}
        />
        <TextField
          label="Ratio to hourly mean (optional)"
          {...errors.field('baseline_ratio')}
          hint="Requires seven days and 168 sampled hours with a positive mean. Threshold remains the minimum count."
          type="number"
          min={1}
          max={100}
          step="any"
          value={fields.ratio}
          onChange={(event) => change({ ratio: event.target.value })}
        />
        <TextField
          label="Baseline window (days)"
          {...errors.field('baseline_days')}
          hint="The sampled hourly mean uses 7 to 30 days, excluding the current hour."
          type="number"
          min={7}
          max={30}
          value={fields.baselineDays}
          onChange={(event) => change({ baselineDays: event.target.value })}
        />
        <TextField
          label="Cooldown (minutes)"
          {...errors.field('cooldown_minutes')}
          hint={`Wait between alerts from this rule: ${String(COOLDOWN_RANGE.min)} to ${String(COOLDOWN_RANGE.max)} minutes (24 hours).`}
          type="number"
          min={COOLDOWN_RANGE.min}
          max={COOLDOWN_RANGE.max}
          value={fields.cooldown}
          onChange={(event) => change({ cooldown: event.target.value })}
        />
        <TextField
          label="Severity floor"
          {...errors.field('severity_floor')}
          hint="0 to 1. Items rated below it are ignored; unrated items count as 0."
          type="number"
          min={0}
          max={1}
          step="0.05"
          value={fields.severityFloor}
          onChange={(event) => change({ severityFloor: event.target.value })}
        />
        <SelectField
          label="Report when it fires"
          {...errors.field('report_template')}
          error={errors.message('report_template') ?? problem}
          hint={
            !fields.template && planProblem
              ? planProblem
              : 'Generated as you, scoped like the alert rule. Country briefs need one country; question reports need a collection plan.'
          }
          value={shape ? '' : fields.template}
          disabled={shape}
          onChange={(event) => change({ template: event.target.value })}
          options={[
            { value: '', label: 'No report' },
            ...available.map((item) => ({ value: item.id, label: item.title })),
            ...(fields.template && !available.some((item) => item.id === fields.template)
              ? [{ value: fields.template, label: `${fields.template} (saved, unavailable)` }]
              : []),
          ]}
        />
      </div>
    </>
  );
}
