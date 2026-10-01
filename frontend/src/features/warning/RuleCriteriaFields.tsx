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

export type RuleFieldKey =
  | 'team_id'
  | 'plan_id'
  | 'area'
  | 'name'
  | 'description'
  | 'categories'
  | 'keywords'
  | 'threshold'
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
}: {
  fields: RuleFields;
  change: (patch: Partial<RuleFields>) => void;
  errors: FieldErrorState<RuleFieldKey>;
  templates: readonly ReportTemplate[];
}) {
  const shape = fields.locationMode === 'shape';
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
          value={fields.window}
          onChange={(event) => change({ window: event.target.value })}
          options={windows}
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
          hint="Generated as you, scoped like the alert rule."
          value={shape ? '' : fields.template}
          disabled={shape}
          onChange={(event) => change({ template: event.target.value })}
          options={[
            { value: '', label: 'No report' },
            ...templates.map((item) => ({ value: item.id, label: item.title })),
            ...(fields.template && !templates.some((item) => item.id === fields.template)
              ? [{ value: fields.template, label: `${fields.template} (saved)` }]
              : []),
          ]}
        />
      </div>
    </>
  );
}
