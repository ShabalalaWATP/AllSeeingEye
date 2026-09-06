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
import type { ReportTemplate } from '@/lib/api/reports';
import type { Schedule, ScheduleRequest } from '@/lib/api/schedules';

const CADENCES = [
  { value: 'daily', label: 'Every day' },
  { value: 'weekdays', label: 'Weekdays' },
  { value: 'weekly', label: 'Once a week' },
];
const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const HOURS = Array.from({ length: 24 }, (_, hour) => ({
  value: String(hour),
  label: `${String(hour).padStart(2, '0')}:00 UTC`,
}));

export function describeCadence(schedule: Schedule): string {
  const at = `${String(schedule.hour_utc).padStart(2, '0')}:00 UTC`;
  if (schedule.cadence === 'weekly') return `${WEEKDAYS[schedule.weekday] ?? ''} at ${at}`;
  if (schedule.cadence === 'weekdays') return `weekdays at ${at}`;
  return `daily at ${at}`;
}

interface ScheduleFormProps {
  templates: readonly ReportTemplate[];
  plans: readonly CollectionPlan[];
  workspaces: Workspaces;
  countries: readonly Country[];
  busy: boolean;
  error: string | null;
  onSubmit: (request: ScheduleRequest) => void;
}

/** A standing order: which product, for which nation, at which UTC hour, how often. */
export function ScheduleForm({
  templates,
  countries,
  busy,
  error,
  onSubmit,
  plans,
  workspaces,
}: ScheduleFormProps) {
  const scope = useWorkspaceSelection(workspaces);
  const [planId, setPlanId] = useState('');
  const matchingPlans = plans.filter(
    (plan) => plan.enabled && (plan.team_id ?? '') === scope.teamId,
  );
  const selectedPlan = matchingPlans.some((plan) => plan.id === planId) ? planId : '';
  const invalidPlan = planId !== '' && selectedPlan === '';
  const [name, setName] = useState('');
  const [template, setTemplate] = useState('intsum');
  const [country, setCountry] = useState('');
  const [question, setQuestion] = useState('');
  const [notifyOnChange, setNotifyOnChange] = useState(false);
  const [researchMode, setResearchMode] = useState<'' | 'quick' | 'detailed'>('');
  const [languages, setLanguages] = useState('en');
  const [focus, setFocus] = useState<NonNullable<ScheduleRequest['research_focus']>>('general');
  const [subject, setSubject] = useState('');
  const needsQuestion = templates.find((item) => item.id === template)?.needs_question === true;
  const languageCodes = languages
    .split(',')
    .map((code) => code.trim().toLowerCase())
    .filter(Boolean);
  const validLanguages =
    languageCodes.length >= 1 &&
    languageCodes.length <= 8 &&
    languageCodes.every((code) => /^[a-z]{2,3}(-[A-Za-z]{2,4})?$/.test(code));
  const subjectScoped = needsQuestion && researchMode !== '' && focus !== 'general';
  const invalidQuestion =
    needsQuestion &&
    ((!question.trim() && (!selectedPlan || researchMode !== '')) ||
      (researchMode !== '' && !validLanguages));
  const [hour, setHour] = useState('6');
  const [cadence, setCadence] = useState<'daily' | 'weekdays' | 'weekly'>('daily');
  const [weekday, setWeekday] = useState('0');
  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!scope.ready || invalidPlan || invalidQuestion) return;
    onSubmit({
      ...(scope.teamId ? { team_id: scope.teamId } : {}),
      ...(selectedPlan ? { plan_id: selectedPlan } : {}),
      ...(needsQuestion && question.trim() ? { question: question.trim() } : {}),
      ...(needsQuestion && researchMode
        ? {
            research_mode: researchMode,
            research_languages: [...new Set(languageCodes)],
            research_focus: focus,
            research_subject: subject.trim() || null,
          }
        : {}),
      research_focus: needsQuestion && researchMode ? focus : 'general',
      notify_on_change: needsQuestion && notifyOnChange,
      name: name.trim(),
      enabled: true,
      template_id: template,
      country_iso: subjectScoped || country === '' ? null : country,
      hour_utc: Number(hour),
      cadence,
      weekday: Number(weekday),
    });
  };
  return (
    <form
      onSubmit={submit}
      aria-label="New schedule"
      className="flex flex-col gap-3 rounded-card border border-line bg-surface p-4"
    >
      {invalidPlan && (
        <Alert tone="error">
          The linked plan is no longer available. Choose a plan in this workspace or select No plan.
        </Alert>
      )}
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
        value={selectedPlan}
        onChange={(event) => setPlanId(event.target.value)}
        hint="Optional. Linked plans must use the same workspace."
        options={[
          { value: '', label: 'No plan' },
          ...matchingPlans.map((plan) => ({ value: plan.id, label: plan.name })),
        ]}
      />
      <div className="grid gap-3 md:grid-cols-3">
        <TextField
          label="Schedule name"
          value={name}
          onChange={(event) => {
            setName(event.target.value);
          }}
          required
          maxLength={120}
        />
        <SelectField
          label="Product"
          value={template}
          onChange={(event) => {
            setTemplate(event.target.value);
          }}
          options={templates
            .filter((item) => !item.needs_conflict && !item.needs_hazard)
            .map((item) => ({ value: item.id, label: item.title }))}
        />
        <SelectField
          label="Nation"
          disabled={subjectScoped}
          value={subjectScoped ? '' : country}
          onChange={(event) => {
            setCountry(event.target.value);
          }}
          options={[
            { value: '', label: 'Whole world' },
            ...countries.map((item) => ({ value: item.iso2, label: item.name })),
          ]}
        />
        <SelectField
          label="Hour"
          value={hour}
          onChange={(event) => {
            setHour(event.target.value);
          }}
          options={HOURS}
        />
        <SelectField
          label="Cadence"
          value={cadence}
          onChange={(event) => {
            const value = event.target.value;
            setCadence(value === 'weekdays' || value === 'weekly' ? value : 'daily');
          }}
          options={CADENCES}
        />
        {cadence === 'weekly' && (
          <SelectField
            label="Weekday"
            value={weekday}
            onChange={(event) => {
              setWeekday(event.target.value);
            }}
            options={WEEKDAYS.map((label, index) => ({ value: String(index), label }))}
          />
        )}
      </div>
      {needsQuestion && (
        <fieldset className="flex flex-col gap-3">
          <legend className="mb-2 text-sm font-medium">Saved research question</legend>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={notifyOnChange}
              onChange={(event) => setNotifyOnChange(event.target.checked)}
            />
            Notify in app when evidence changes
          </label>
          <p className="text-xs text-muted">
            The first successful run establishes a baseline. Later alerts compare evidence, source
            flags and recorded assessments. This does not verify importance, corrections or
            retractions.
          </p>
          <TextAreaField
            label="Question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            maxLength={1000}
            required={!selectedPlan || researchMode !== ''}
            hint="Repeated at each scheduled run. A collection plan can supply the question when using live evidence."
          />
          <SelectField
            label="Collection depth"
            value={researchMode}
            onChange={(event) => setResearchMode(event.target.value as '' | 'quick' | 'detailed')}
            options={[
              { value: '', label: 'Existing live evidence' },
              { value: 'quick', label: 'Quick research' },
              { value: 'detailed', label: 'Detailed research' },
            ]}
            hint="Research uses bounded public-source collection and the configured assessment model each run. It creates a report every time, even if little has changed."
          />
          {researchMode && (
            <>
              <TextField
                label="Research languages"
                value={languages}
                onChange={(event) => setLanguages(event.target.value)}
                maxLength={64}
                hint="One to eight comma-separated language codes, for example en, uk."
                error={validLanguages ? undefined : 'Enter one to eight valid language codes.'}
              />
              <SelectField
                label="Research focus"
                value={focus}
                onChange={(event) => {
                  setFocus(event.target.value as typeof focus);
                  if (event.target.value !== 'general') setCountry('');
                }}
                options={['general', 'company', 'domain', 'document', 'media'].map((value) => ({
                  value,
                  label: value.charAt(0).toUpperCase() + value.slice(1),
                }))}
              />
              <TextField
                label="Research subject"
                value={subject}
                onChange={(event) => setSubject(event.target.value)}
                maxLength={300}
                hint="Optional organisation, domain or document URL to focus the question."
              />
            </>
          )}
        </fieldset>
      )}
      {error === null ? null : <Alert tone="error">{error}</Alert>}
      <div>
        <Button type="submit" busy={busy} disabled={!scope.ready || invalidPlan || invalidQuestion}>
          Add schedule
        </Button>
      </div>
    </form>
  );
}
