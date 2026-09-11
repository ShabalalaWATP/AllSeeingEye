import { useState } from 'react';
import type { SyntheticEvent } from 'react';

import { CountryMultiSelect } from '@/components/research/CountryMultiSelect';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField, TextField } from '@/components/ui/Field';
import { WorkspaceField } from '@/components/ui/WorkspaceField';
import type { CollectionPlan } from '@/lib/api/direction';
import type { Country } from '@/lib/api/geoSchemas';
import type { ReportTemplate } from '@/lib/api/reports';
import type { ScheduleRequest } from '@/lib/api/schedules';
import { useWorkspaceSelection } from '@/lib/hooks/useWorkspaces';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';

import { ScheduleSources } from './ScheduleSources';
import { ScheduleTiming } from './ScheduleTiming';
import type { Cadence } from './ScheduleTiming';

interface ScheduleFormProps {
  templates: readonly ReportTemplate[];
  plans: readonly CollectionPlan[];
  workspaces: Workspaces;
  countries: readonly Country[];
  busy: boolean;
  error: string | null;
  onSubmit: (request: ScheduleRequest) => void;
}

/** Save the question, coverage and source choices that every recurring run will reuse. */
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
  const [template, setTemplate] = useState('ask');
  const [selectedCountries, setCountries] = useState<string[]>([]);
  const [question, setQuestion] = useState('');
  const [notifyOnChange, setNotifyOnChange] = useState(true);
  const [researchMode, setResearchMode] = useState<'' | 'quick' | 'detailed'>('quick');
  const [languages, setLanguages] = useState('en');
  const [focus, setFocus] = useState<NonNullable<ScheduleRequest['research_focus']>>('general');
  const [subject, setSubject] = useState('');
  const [webSearch, setWebSearch] = useState(false);
  const [sourceIds, setSourceIds] = useState<string[] | null>(null);
  const [chooseSources, setChooseSources] = useState(false);
  const [hour, setHour] = useState('6');
  const [cadence, setCadence] = useState<Cadence>('weekly');
  const [weekday, setWeekday] = useState('0');
  const [monthday, setMonthday] = useState('1');
  const [lookback, setLookback] = useState('7');
  const product = templates.find((item) => item.id === template);
  const needsQuestion = product?.needs_question === true;
  const activeResearch = needsQuestion && researchMode !== '';
  const languageCodes = [
    ...new Set(
      languages
        .split(',')
        .map((code) => code.trim().toLowerCase())
        .filter(Boolean),
    ),
  ];
  const validLanguages =
    languageCodes.length >= 1 &&
    languageCodes.length <= 8 &&
    languageCodes.every((code) => /^[a-z]{2,3}(-[a-z]{2,4})?$/.test(code));
  const subjectScoped = activeResearch && focus !== 'general';
  const countriesInScope = subjectScoped ? [] : selectedCountries;
  const invalidQuestion =
    needsQuestion &&
    ((!question.trim() && (!selectedPlan || activeResearch)) ||
      (activeResearch && !validLanguages) ||
      (subjectScoped && !subject.trim()));
  const validWindow =
    Number.isInteger(Number(lookback)) && Number(lookback) >= 1 && Number(lookback) <= 730;
  const invalidCountry = product?.needs_country === true && countriesInScope.length !== 1;
  const invalid =
    !scope.ready || !product || invalidPlan || invalidQuestion || invalidCountry || !validWindow;
  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (invalid) return;
    onSubmit({
      ...(scope.teamId ? { team_id: scope.teamId } : {}),
      ...(selectedPlan ? { plan_id: selectedPlan } : {}),
      ...(needsQuestion && question.trim() ? { question: question.trim() } : {}),
      ...(activeResearch
        ? {
            research_mode: researchMode,
            research_languages: languageCodes,
            research_subject: subject.trim() || null,
            research_web_search: webSearch,
            research_source_ids: sourceIds,
          }
        : {}),
      research_focus: activeResearch ? focus : 'general',
      notify_on_change: needsQuestion && notifyOnChange,
      name: name.trim(),
      enabled: true,
      template_id: template,
      country_iso: countriesInScope.length === 1 ? (countriesInScope[0] ?? null) : null,
      country_isos: countriesInScope,
      research_web_search: activeResearch && webSearch,
      window_hours: Number(lookback) * 24,
      hour_utc: Number(hour),
      cadence,
      weekday: Number(weekday),
      monthday: Number(monthday),
    });
  };
  return (
    <form
      onSubmit={submit}
      aria-label="New schedule"
      className="space-y-5 rounded-lg border border-line bg-surface p-5 sm:p-6"
    >
      <div>
        <h3 className="text-lg font-semibold">Set research to repeat</h3>
        <p className="mt-1 text-sm text-muted">
          Save a question once. Receive a fresh report every week or month.
        </p>
      </div>
      {invalidPlan && (
        <Alert tone="error">
          The linked plan is no longer available. Choose a plan in this workspace or select No plan.
        </Alert>
      )}
      <TextField
        label="Schedule name"
        value={name}
        onChange={(event) => setName(event.target.value)}
        required
        maxLength={120}
        placeholder="Weekly energy developments"
      />
      {needsQuestion && (
        <TextAreaField
          label="Question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          maxLength={1000}
          required={!selectedPlan || activeResearch}
          placeholder="What has changed, what is supported by evidence, and what should I watch next?"
        />
      )}
      {product?.needs_country ? (
        <SelectField
          label="Nation"
          value={countriesInScope[0] ?? ''}
          onChange={(event) => setCountries(event.target.value ? [event.target.value] : [])}
          options={[
            { value: '', label: 'Choose one nation' },
            ...countries.map((item) => ({ value: item.iso2, label: item.name })),
          ]}
        />
      ) : (
        <CountryMultiSelect
          countries={countries}
          value={countriesInScope}
          onChange={setCountries}
          disabled={subjectScoped}
        />
      )}
      {subjectScoped && (
        <p className="text-xs text-muted">
          This focused search uses the organisation or domain rather than country filters.
        </p>
      )}
      <ScheduleTiming
        cadence={cadence}
        hour={hour}
        weekday={weekday}
        monthday={monthday}
        lookback={lookback}
        onCadence={setCadence}
        onHour={setHour}
        onWeekday={setWeekday}
        onMonthday={setMonthday}
        onLookback={setLookback}
      />
      {needsQuestion && (
        <fieldset className="space-y-3 border-t border-line pt-5">
          <legend className="text-sm font-semibold">Collection and notifications</legend>
          <SelectField
            label="Collection depth"
            value={researchMode}
            onChange={(event) => setResearchMode(event.target.value as typeof researchMode)}
            options={[
              { value: 'quick', label: 'Quick research' },
              { value: 'detailed', label: 'Detailed research' },
              { value: '', label: 'Existing live evidence only' },
            ]}
            hint="Quick and detailed runs query supported sources within request limits. Historical coverage varies by provider."
          />
          {activeResearch && (
            <label className="flex items-start gap-3 text-sm">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 accent-ember"
                checked={webSearch}
                onChange={(event) => setWebSearch(event.target.checked)}
              />
              <span>
                Include a fresh web search
                <span className="mt-1 block text-xs text-muted">
                  Uses the workspace's configured model connection at every run, where supported.
                  Provider usage may incur charges.
                </span>
              </span>
            </label>
          )}
          <label className="flex items-start gap-3 text-sm">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 accent-ember"
              checked={notifyOnChange}
              onChange={(event) => setNotifyOnChange(event.target.checked)}
            />
            <span>
              Notify in app when evidence changes
              <span className="mt-1 block text-xs text-muted">
                The first report establishes a baseline. Later runs compare evidence and
                assessments; an alert is not verification.
              </span>
            </span>
          </label>
        </fieldset>
      )}
      <details className="rounded-md border border-line bg-ground p-3">
        <summary className="cursor-pointer text-sm font-medium">Advanced scope and sources</summary>
        <div className="mt-4 space-y-4">
          <WorkspaceField
            workspaces={workspaces}
            value={scope.teamId}
            onChange={(value) => {
              scope.select(value);
              setPlanId('');
            }}
          />
          <SelectField
            label="Product"
            value={template}
            onChange={(event) => setTemplate(event.target.value)}
            options={templates
              .filter((item) => !item.needs_conflict && !item.needs_hazard)
              .map((item) => ({ value: item.id, label: item.title }))}
          />
          <SelectField
            label="Collection plan"
            value={selectedPlan}
            onChange={(event) => setPlanId(event.target.value)}
            hint="Optional. Plans must use the same workspace."
            options={[
              { value: '', label: 'No plan' },
              ...matchingPlans.map((plan) => ({ value: plan.id, label: plan.name })),
            ]}
          />
          {activeResearch && (
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
                  setSourceIds(null);
                }}
                options={['general', 'company', 'domain'].map((value) => ({
                  value,
                  label: value.charAt(0).toUpperCase() + value.slice(1),
                }))}
              />
              {focus !== 'general' && (
                <TextField
                  label="Research subject"
                  value={subject}
                  onChange={(event) => setSubject(event.target.value)}
                  maxLength={300}
                  required
                  hint="Organisation name, registry identifier or domain."
                />
              )}
              <Button
                variant="secondary"
                disabled={invalidQuestion || !validWindow}
                onClick={() => setChooseSources(!chooseSources)}
              >
                {chooseSources ? 'Hide source choices' : 'Choose research sources'}
              </Button>
              {chooseSources && !invalidQuestion && validWindow && (
                <ScheduleSources
                  scope={{
                    question: question.trim(),
                    mode: researchMode,
                    languages: languageCodes,
                    focus,
                    subject: subject.trim() || null,
                    countries: countriesInScope,
                    research_web_search: webSearch,
                  }}
                  lookback={Number(lookback)}
                  value={sourceIds}
                  onChange={setSourceIds}
                />
              )}
              {sourceIds !== null && (
                <p className="text-xs text-muted">
                  {sourceIds.length} explicit source choices saved. Newly added sources are included
                  only when you use all supported sources.
                </p>
              )}
            </>
          )}
        </div>
      </details>
      {error !== null && <Alert tone="error">{error}</Alert>}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
        <p className="text-xs text-muted">
          Saved to {workspaces.label(scope.teamId || null)}. Pause future runs at any time.
        </p>
        <Button type="submit" busy={busy} disabled={invalid}>
          Add schedule
        </Button>
      </div>
    </form>
  );
}
