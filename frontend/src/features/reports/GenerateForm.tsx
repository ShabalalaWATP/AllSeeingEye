import { ReportOptions } from '@/components/reports/ReportOptions';
import type { Profile } from '@/lib/api/profile';
import { useState } from 'react';
import type { SyntheticEvent } from 'react';

import { WorkspaceField } from '@/components/ui/WorkspaceField';
import type { CollectionPlan } from '@/lib/api/direction';
import { useWorkspaceSelection } from '@/lib/hooks/useWorkspaces';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField, TextField } from '@/components/ui/Field';
import type { Country } from '@/lib/api/geoSchemas';
import type { ReportRequest, ReportTemplate } from '@/lib/api/reports';

export interface Choice {
  id: string;
  label: string;
}

export interface GenerateFormProps {
  preferences?: Profile;
  templates: readonly ReportTemplate[];
  plans: readonly CollectionPlan[];
  workspaces: Workspaces;
  countries: readonly Country[];
  conflicts: readonly Choice[];
  hazards: readonly Choice[];
  initial?: Partial<Record<'template' | 'country' | 'conflict' | 'hazard' | 'plan', string>>;
  busy: boolean;
  error: string | null;
  onSubmit: (request: ReportRequest) => void;
}

/** Choose a product and its scope: a nation, a question, a curated conflict or a hazard. */
export function GenerateForm({
  preferences,
  templates,
  plans,
  workspaces,
  countries,
  conflicts,
  hazards,
  initial = {},
  busy,
  error,
  onSubmit,
}: GenerateFormProps) {
  const scope = useWorkspaceSelection(workspaces);
  const [reportLanguage, setReportLanguage] = useState<
    NonNullable<ReportRequest['report_language']>
  >(preferences?.report_language ?? 'en');
  const [reportStyle, setReportStyle] = useState<NonNullable<ReportRequest['report_style']>>(
    preferences?.report_style ?? 'assessment',
  );
  const [planId, setPlanId] = useState(initial.plan ?? '');
  const matchingPlans = plans.filter(
    (plan) => plan.enabled && (plan.team_id ?? '') === scope.teamId,
  );
  const selectedPlan = matchingPlans.find((plan) => plan.id === planId);
  const invalidPlan = planId !== '' && selectedPlan === undefined;
  const [templateId, setTemplateId] = useState(initial.template ?? templates[0]?.id ?? 'intsum');
  const [country, setCountry] = useState(initial.country ?? '');
  const [conflict, setConflict] = useState(initial.conflict ?? '');
  const [hazard, setHazard] = useState(initial.hazard ?? '');
  const [question, setQuestion] = useState('');
  const [windowHours, setWindowHours] = useState('');
  const [advocacy, setAdvocacy] = useState(false);
  const template = templates.find((item) => item.id === templateId) ?? templates[0];

  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!scope.ready || invalidPlan) return;
    const request: ReportRequest = {
      disclose_area_to_provider: false,
      template: templateId,
      report_language: reportLanguage,
      report_style: reportStyle,
      research_focus: 'general',
      devils_advocacy: advocacy,
      ...(scope.teamId ? { team_id: scope.teamId } : {}),
    };
    if (country !== '') request.country = country;
    if (template?.needs_conflict && conflict !== '') request.conflict = conflict;
    if (template?.needs_hazard && hazard !== '') request.hazard = hazard;
    if (question.trim() !== '') request.question = question.trim();
    if (windowHours.trim() !== '') request.window_hours = Number(windowHours);
    if (advocacy) request.devils_advocacy = true;
    if (selectedPlan) request.plan = selectedPlan.id;
    onSubmit(request);
  };

  return (
    <form
      onSubmit={submit}
      aria-label="Generate a report"
      className="flex flex-col gap-4 rounded-card border border-line bg-surface p-4"
    >
      <WorkspaceField
        workspaces={workspaces}
        value={scope.teamId}
        onChange={(value) => {
          scope.select(value);
          setPlanId('');
        }}
      />
      <SelectField
        label="Collection plan"
        value={selectedPlan?.id ?? ''}
        onChange={(event) => setPlanId(event.target.value)}
        hint="Optional. A report and its linked plan must use the same workspace."
        options={[
          { value: '', label: 'No plan' },
          ...matchingPlans.map((plan) => ({ value: plan.id, label: plan.name })),
        ]}
      />
      {invalidPlan && (
        <Alert tone="error">
          The requested plan is unavailable in this workspace. Choose its team and plan, or select
          No plan.
        </Alert>
      )}
      <div className="grid gap-4 md:grid-cols-3">
        <SelectField
          label="Product"
          value={templateId}
          onChange={(event) => {
            setTemplateId(event.target.value);
          }}
          options={templates.map((item) => ({ value: item.id, label: item.title }))}
        />
        {template?.needs_conflict ? (
          <SelectField
            label="Conflict"
            hint="From the conflict tracker."
            value={conflict}
            onChange={(event) => {
              setConflict(event.target.value);
            }}
            options={[
              { value: '', label: 'Choose a conflict' },
              ...conflicts.map((item) => ({ value: item.id, label: item.label })),
            ]}
          />
        ) : template?.needs_hazard ? (
          <SelectField
            label="Hazard"
            hint="From the disaster tracker."
            value={hazard}
            onChange={(event) => {
              setHazard(event.target.value);
            }}
            options={[
              { value: '', label: 'Choose a hazard' },
              ...hazards.map((item) => ({ value: item.id, label: item.label })),
            ]}
          />
        ) : null}
        <SelectField
          label="Nation"
          hint={template?.needs_country ? 'Required for this product.' : 'Optional scope.'}
          value={country}
          onChange={(event) => {
            setCountry(event.target.value);
          }}
          options={[
            { value: '', label: 'Whole world' },
            ...countries.map((item) => ({ value: item.iso2, label: item.name })),
          ]}
        />
        <TextField
          label="Window (hours)"
          type="number"
          min={1}
          max={336}
          placeholder={template ? String(template.window_hours) : ''}
          value={windowHours}
          onChange={(event) => {
            setWindowHours(event.target.value);
          }}
        />
      </div>
      {selectedPlan !== undefined && (
        <p className="text-sm text-muted">
          Scoped by a collection plan: its area, nations, requirements and background steer the
          evidence, and its first requirement is the question unless you ask another.
        </p>
      )}
      {template?.needs_question && (
        <TextAreaField
          label="Question"
          hint="What do you want the Eye to assess from the live evidence?"
          value={question}
          onChange={(event) => {
            setQuestion(event.target.value);
          }}
          required={selectedPlan === undefined}
          maxLength={1000}
        />
      )}
      <label className="flex items-center gap-2 text-sm text-text">
        <input
          type="checkbox"
          checked={advocacy}
          onChange={(event) => {
            setAdvocacy(event.target.checked);
          }}
          className="accent-ember"
        />
        Devil&apos;s advocacy: a second model call attacks the top judgement and can lower its
        confidence
      </label>
      <ReportOptions
        language={reportLanguage}
        style={reportStyle}
        onLanguage={setReportLanguage}
        onStyle={setReportStyle}
        disabled={busy}
      />
      {template && <p className="text-sm text-muted">{template.purpose}</p>}
      {error === null ? null : <Alert tone="error">{error}</Alert>}
      <div>
        <Button
          type="submit"
          busy={busy}
          disabled={templates.length === 0 || !scope.ready || invalidPlan}
        >
          Generate
        </Button>
      </div>
    </form>
  );
}
