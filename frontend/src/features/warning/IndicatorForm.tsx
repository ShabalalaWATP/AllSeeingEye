import { useState } from 'react';
import type { SyntheticEvent } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField, TextField } from '@/components/ui/Field';
import { FormErrors } from '@/components/ui/FormErrors';
import { WorkspaceField } from '@/components/ui/WorkspaceField';
import type { IndicatorRequest, RuleFields } from '@/lib/alertRules';
import { MAX_DESCRIPTION, ruleProblems, ruleRequest, ruleSummary } from '@/lib/alertRules';
import type { ReportWatchDraft } from '@/lib/alertRuleDraft';
import type { CollectionPlan } from '@/lib/api/direction';
import { ApiError } from '@/lib/api/errors';
import { useFieldErrors } from '@/lib/api/fieldErrors';
import type { Country } from '@/lib/api/geoSchemas';
import type { ReportTemplate } from '@/lib/api/reports';
import type { Indicator } from '@/lib/api/warning';
import type { AreaWatchDraft } from '@/lib/areaWatchDraft';
import { draftForms, useDraftState, useHasDraft } from '@/lib/formDrafts';
import { useUnloadWarning } from '@/lib/hooks/useUnloadWarning';
import { useWorkspaceSelection } from '@/lib/hooks/useWorkspaces';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';
import { useAuthStore } from '@/stores/auth';

import { IndicatorAreaFields, useIndicatorArea } from './IndicatorAreaFields';
import { InstallationCopyNotice } from './InstallationCopyNotice';
import { initialRuleFields, widenedLabels } from './ruleFormSetup';
import { RuleCriteriaFields } from './RuleCriteriaFields';
import type { RuleFieldKey } from './RuleCriteriaFields';
import { AreaDraftNotice, ReportDraftNotice } from './RuleDraftNotice';
import { RuleSummary } from './RuleSummary';

/** Form fields for the API paths an alert rule request can reject. */
const RULE_FIELDS = {
  team_id: 'Workspace',
  plan_id: 'Collection plan',
  area: { label: 'Watch location', paths: ['countries', 'bbox', 'research_area'] },
  name: 'Alert rule name',
  description: 'Notes',
  categories: 'Event categories',
  keywords: 'Keywords',
  threshold: 'Threshold',
  baseline_ratio: 'Ratio to hourly mean',
  baseline_days: 'Baseline window',
  window_minutes: 'Window',
  cooldown_minutes: 'Cooldown',
  severity_floor: 'Severity floor',
  report_template: 'Report when it fires',
  confirm_wider_scope: 'Confirm wider scope',
} as const;

export type RuleFormMode =
  | { kind: 'create'; areaDraft: AreaWatchDraft | null; reportDraft: ReportWatchDraft | null }
  | { kind: 'edit'; rule: Indicator };

interface IndicatorFormProps {
  mode: RuleFormMode;
  templates: readonly ReportTemplate[];
  /** The caller's plans, or null while they are loading or unavailable. */
  plans: readonly CollectionPlan[] | null;
  workspaces: Workspaces;
  /** The country catalogue, or null while it is loading or unavailable. */
  countries: readonly Country[] | null;
  busy: boolean;
  /** The failed save, mapped to field reasons or a safe message. */
  error: unknown;
  onSubmit: (request: IndicatorRequest, options: { confirmWider: boolean }) => void;
  onDiscardDraft: () => void;
  onCancel?: () => void;
}

function draftName(mode: RuleFormMode): string | null {
  if (mode.kind === 'edit') return null; // An edit of a saved rule keeps no draft.
  if (mode.reportDraft) return draftForms.alertRule(`report-${String(mode.reportDraft.id)}`);
  return draftForms.alertRule(mode.areaDraft?.id);
}

/** An alert rule: what to watch, how many in what window, and what to do when it fires. */
export function IndicatorForm(props: IndicatorFormProps) {
  const { mode, templates, busy, error, onSubmit, plans, workspaces, countries } = props;
  const user = useAuthStore((state) => state.user);
  const form = draftName(mode);
  const editing = mode.kind === 'edit' ? mode.rule : null;
  const reportDraft = mode.kind === 'create' ? mode.reportDraft : null;
  const areaDraft = mode.kind === 'create' ? mode.areaDraft : null;
  const scope = useWorkspaceSelection(workspaces, form, reportDraft?.source.teamId ?? '');
  useUnloadWarning(useHasDraft(form));
  const [fields, setFields] = useDraftState<RuleFields>(form, 'rule', () =>
    initialRuleFields(mode),
  );
  const change = (patch: Partial<RuleFields>) => setFields((current) => ({ ...current, ...patch }));
  const [confirmWider, setConfirmWider] = useState(false);
  const [checked, setChecked] = useState<ApiError | null>(null);
  const area = useIndicatorArea(
    areaDraft?.bounds ??
      (editing?.bbox
        ? {
            west: editing.bbox[0] ?? 0,
            south: editing.bbox[1] ?? 0,
            east: editing.bbox[2] ?? 0,
            north: editing.bbox[3] ?? 0,
          }
        : null),
    // The canonical GeoJSON collection a map hand-off froze, sent back exactly as it was.
    (areaDraft?.geometry as Record<string, unknown> | undefined) ??
      editing?.research_area?.geometry ??
      reportDraft?.geometry ??
      undefined,
    fields.locationMode === 'area',
  );

  const teamId = editing ? (editing.team_id ?? '') : scope.teamId;
  const owner = editing?.created_by ?? user?.id ?? '';
  const matchingPlans = (plans ?? []).filter(
    (plan) =>
      plan.enabled &&
      (plan.team_id ?? '') === teamId &&
      (teamId !== '' || plan.created_by === owner),
  );
  // An unloaded or failed plan list cannot show that a link is stale, only that it is unknown.
  const unknownPlan = fields.planId !== '' && plans === null;
  const invalidPlan =
    fields.planId !== '' && plans !== null && !matchingPlans.some((p) => p.id === fields.planId);
  const reportTeam = reportDraft?.source.teamId ?? null;
  const team = workspaces.teams.find((entry) => entry.team.id === reportTeam)?.team;
  const lostTeam =
    reportTeam !== null &&
    !workspaces.loading &&
    (team === undefined || (!team.is_active && user?.role !== 'admin'));
  const known = countries === null ? null : new Set(countries.map((country) => country.iso2));
  const problems: Record<string, string> = ruleProblems(fields, { knownCountries: known });
  if (fields.locationMode === 'area' && area.error) problems.bbox = area.error;
  if (invalidPlan)
    problems.plan_id =
      'The linked plan is unavailable. Choose a plan in this workspace or No plan (remove link).';
  if (lostTeam)
    problems.team_id =
      "You can no longer create alert rules in the report's team. Discard this draft; it is not moved to another workspace.";
  const widened = editing ? widenedLabels(editing, fields) : [];
  if (widened.length > 0 && !confirmWider)
    problems.confirm_wider_scope = 'Confirm the wider scope, or choose specific values.';

  const errors = useFieldErrors<RuleFieldKey | 'confirm_wider_scope'>(
    checked ?? error,
    RULE_FIELDS,
  );
  const countryName = (code: string) =>
    countries?.find((country) => country.iso2 === code)?.name ?? `Unknown country ${code}`;
  const retained = (key: 'countries' | 'categories') =>
    problems[key]?.startsWith('Remove unknown') ? problems[key] : undefined;

  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy) return;
    const blocking =
      scope.ready || editing || 'team_id' in problems
        ? problems
        : { ...problems, team_id: 'Choose an available workspace.' };
    if (Object.keys(blocking).length > 0) {
      setChecked(
        new ApiError(422, 'validation_error', 'Check these fields and try again.', blocking),
      );
      return;
    }
    setChecked(null);
    onSubmit(ruleRequest(fields, { teamId, bbox: area.bbox, geometry: area.geometry }), {
      confirmWider: widened.length > 0,
    });
  };

  const label = editing ? `Edit alert rule ${editing.name}` : 'New alert rule';
  return (
    <form
      onSubmit={submit}
      aria-label={label}
      noValidate
      className="flex flex-col gap-3 rounded-card border border-line bg-surface p-4"
    >
      <h3 className="text-sm font-semibold">{editing ? label : 'New alert rule'}</h3>
      {areaDraft && <AreaDraftNotice draft={areaDraft} onDiscard={props.onDiscardDraft} />}
      {reportDraft && <ReportDraftNotice draft={reportDraft} onDiscard={props.onDiscardDraft} />}
      <InstallationCopyNotice />
      <p className="text-xs text-muted">
        Save the rule, then open Notifications to choose email and a registered webhook.
      </p>
      {invalidPlan && (
        <Alert tone="error">
          The linked plan is no longer available. Choose a plan in this workspace or select No plan
          (remove link) to save without it.
        </Alert>
      )}
      <div id={errors.id('team_id')}>
        {editing ? (
          <p className="text-sm">
            <span className="font-medium">Workspace:</span> {workspaces.label(editing.team_id)}.
            Editing never moves an alert rule to another workspace.
          </p>
        ) : (
          <WorkspaceField
            workspaces={workspaces}
            value={scope.teamId}
            disabled={reportDraft !== null}
            onChange={(value) => {
              scope.select(value);
              change({ planId: '' });
            }}
          />
        )}
        {reportDraft && (
          <p className="mt-1 text-xs text-muted">
            Drafts from a report stay in the report&apos;s own workspace.
          </p>
        )}
        {lostTeam && <Alert tone="error">{problems.team_id}</Alert>}
      </div>
      <SelectField
        label="Collection plan"
        {...errors.field('plan_id')}
        value={fields.planId}
        onChange={(event) => change({ planId: event.target.value })}
        hint="Optional. Only plans in the same workspace and with the same owner are listed."
        options={[
          { value: '', label: invalidPlan ? 'No plan (remove link)' : 'No plan' },
          ...(invalidPlan ? [{ value: fields.planId, label: 'Unavailable plan' }] : []),
          ...(unknownPlan
            ? [{ value: fields.planId, label: 'Linked plan (list not loaded)' }]
            : []),
          ...matchingPlans.map((plan) => ({ value: plan.id, label: plan.name })),
        ]}
      />
      <TextField
        label="Alert rule name"
        {...errors.field('name')}
        value={fields.name}
        onChange={(event) => change({ name: event.target.value })}
        required
      />
      <TextAreaField
        label="Notes"
        {...errors.field('description')}
        hint={`Optional, up to ${String(MAX_DESCRIPTION)} characters. Shown with the rule only.`}
        value={fields.description}
        onChange={(event) => change({ description: event.target.value })}
      />
      <div id={errors.id('area')}>
        <IndicatorAreaFields
          mode={fields.locationMode}
          onModeChange={(locationMode) => change({ locationMode })}
          value={area}
          countries={fields.countries}
          onCountriesChange={(next) => change({ countries: next })}
          catalogue={countries}
          countriesError={errors.message('area') ?? retained('countries')}
        />
      </div>
      <RuleCriteriaFields
        fields={fields}
        change={change}
        errors={{
          ...errors,
          message: (key) =>
            errors.message(key) ?? (key === 'categories' ? retained(key) : undefined),
        }}
        templates={templates}
      />
      <RuleSummary
        rows={ruleSummary(fields, {
          countryName,
          templateName: (id) => templates.find((item) => item.id === id)?.title ?? id,
          bbox: area.bbox,
        })}
        status={fields.enabled ? 'Active once saved' : 'Paused: saving keeps it paused'}
      />
      {widened.length > 0 && (
        <label id={errors.id('confirm_wider_scope')} className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            checked={confirmWider}
            onChange={(event) => setConfirmWider(event.target.checked)}
            className="mt-1 h-4 w-4 accent-ember"
          />
          <span>
            I understand this alert rule will no longer be restricted by {widened.join(', ')}.
          </span>
        </label>
      )}
      <FormErrors errors={errors} />
      <div className="flex flex-wrap gap-2">
        <Button type="submit" busy={busy}>
          {editing ? 'Save changes' : 'Add alert rule'}
        </Button>
        {props.onCancel && (
          <Button type="button" variant="secondary" disabled={busy} onClick={props.onCancel}>
            Cancel editing
          </Button>
        )}
      </div>
    </form>
  );
}
