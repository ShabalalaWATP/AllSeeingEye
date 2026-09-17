import { useRef, useState, type SyntheticEvent } from 'react';
import { CountryMultiSelect } from '@/components/research/CountryMultiSelect';
import { ResearchDepth } from '@/components/research/ResearchDepth';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField, TextField } from '@/components/ui/Field';
import type { Country } from '@/lib/api/geoSchemas';
import { SubscriptionCoverage } from './SubscriptionCoverage';
import { focusScheduleIssue, scheduleIssueTarget } from './scheduleFormFocus';
import { ScheduleScope } from './ScheduleScope';
import { SubscriptionCostNote } from './SubscriptionCostNote';
import { ScheduleTiming } from './ScheduleTiming';
import { useScheduleForm, type ScheduleFormStateProps } from './useScheduleForm';

export function ScheduleForm(
  props: ScheduleFormStateProps & {
    countries: readonly Country[];
    error: string | null;
    onCancel?: (() => void) | undefined;
    duplicate?: boolean;
  },
) {
  const { templates, workspaces, countries, busy, error, initial, onCancel, duplicate } = props;
  const state = useScheduleForm(props);
  const form = useRef<HTMLFormElement>(null);
  const [attempted, setAttempted] = useState(false);
  const {
    scope,
    invalidPlan,
    name,
    setName,
    needsQuestion,
    question,
    setQuestion,
    selectedPlan,
    activeResearch,
    researchMode,
    setResearchMode,
    liveOnly,
    setLiveOnly,
    product,
    countriesInScope,
    setCountries,
    subjectScoped,
    hour,
    setHour,
    cadence,
    setCadence,
    weekday,
    setWeekday,
    monthday,
    setMonthday,
    lookback,
    lookbackUnit,
    changeLookbackUnit,
    setLookback,
    webSearch,
    setWebSearch,
    notifyOnChange,
    setNotifyOnChange,
    invalid,
    submit,
  } = state;
  const validateSubmit = (event: SyntheticEvent<HTMLFormElement>) => {
    if (invalid) {
      event.preventDefault();
      setAttempted(true);
      if (state.issues[0]) focusScheduleIssue(form.current, state.issues[0]);
      return;
    }
    submit(event);
  };
  return (
    <form
      ref={form}
      onSubmit={validateSubmit}
      aria-label={
        duplicate ? 'Duplicate subscription' : initial ? 'Edit subscription' : 'New subscription'
      }
      noValidate
      className="min-w-0 border-t border-line pt-7"
    >
      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h2 tabIndex={-1} className="text-xl font-semibold">
            {duplicate
              ? 'Duplicate subscription'
              : initial
                ? 'Edit subscription'
                : 'Create a subscription'}
          </h2>
          <p className="mt-2 text-sm text-muted">
            Choose what you want to follow, the report depth and how often to receive an update.
          </p>
        </div>
        {onCancel && (
          <Button variant="ghost" onClick={onCancel} disabled={busy}>
            Cancel
          </Button>
        )}
      </header>
      {attempted && state.issues.length > 0 && (
        <Alert tone="error">
          <p>Check these fields before saving:</p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {state.issues.map((issue) => (
              <li key={issue.field}>
                <a
                  href={`#${scheduleIssueTarget(issue)}`}
                  className="underline underline-offset-2"
                  onClick={(event) => {
                    event.preventDefault();
                    focusScheduleIssue(form.current, issue);
                  }}
                >
                  {issue.field}: {issue.message}
                </a>
              </li>
            ))}
          </ul>
        </Alert>
      )}
      {error !== null && <Alert tone="error">{error}</Alert>}
      <fieldset
        disabled={busy}
        className="grid min-w-0 gap-8 disabled:opacity-70 xl:grid-cols-[minmax(0,1fr)_20rem]"
      >
        <div className="min-w-0 space-y-5">
          {invalidPlan && (
            <Alert tone="error">
              The linked plan is no longer available. Choose a plan in this workspace or select No
              plan.
            </Alert>
          )}
          <div id="subscription-name">
            <TextField
              label="Subscription name"
              error={attempted && !name.trim() ? 'Enter a subscription name.' : undefined}
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
              maxLength={120}
              placeholder="Weekly energy developments"
            />
          </div>
          {needsQuestion && (
            <div id="subscription-question">
              <TextAreaField
                label="Question"
                error={
                  attempted && state.issues.some((issue) => issue.field === 'Question')
                    ? 'Enter a question.'
                    : undefined
                }
                hint="Any topic: a conflict, natural disaster, industry, organisation or local situation."
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                rows={3}
                className="min-h-28 resize-y bg-surface p-4 text-base leading-relaxed"
                maxLength={1000}
                required={!selectedPlan || activeResearch}
                placeholder="What has changed, what is supported by evidence, and what should I watch next?"
              />
            </div>
          )}
          {needsQuestion && (
            <ResearchDepth value={researchMode} onChange={setResearchMode} disabled={liveOnly} />
          )}
          <h3 className="border-t border-line pt-5 text-sm font-semibold">Scope and sources</h3>
          <div id="subscription-countries">
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
                disabled={subjectScoped || Boolean(activeResearch && state.researchArea)}
              />
            )}
          </div>
          {needsQuestion && !subjectScoped && (
            <div id="subscription-coverage">
              <SubscriptionCoverage state={state} />
            </div>
          )}
          {subjectScoped && (
            <p className="text-xs text-muted">
              This focused search uses the organisation or domain rather than country filters.
            </p>
          )}

          {needsQuestion && (
            <label className="flex items-start gap-3 text-sm">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 accent-ember"
                checked={liveOnly}
                disabled={Boolean(state.researchArea)}
                onChange={(event) => setLiveOnly(event.target.checked)}
              />
              <span>
                Use existing live evidence only
                <span className="mt-1 block text-xs text-muted">
                  {state.researchArea
                    ? 'Clear the fixed boundary first to change collection mode.'
                    : 'Skip new source collection and use the live evidence already available.'}
                </span>
              </span>
            </label>
          )}
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
                  Uses the workspace connection at each run, where supported. Provider usage may
                  incur charges.
                </span>
              </span>
            </label>
          )}
          <ScheduleScope
            state={state}
            workspaces={workspaces}
            templates={templates}
            initial={Boolean(initial)}
          />
        </div>
        <aside
          id="subscription-timing"
          aria-label="Subscription timing"
          className="min-w-0 space-y-5 self-start rounded-xl bg-surface p-5 xl:sticky xl:top-4"
        >
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-ember">
              Your update schedule
            </p>
            <p className="mt-2 text-sm text-muted">
              Updates appear in the app as complete reports with citations and export options.
            </p>
          </div>
          <ScheduleTiming
            cadence={cadence}
            hour={hour}
            weekday={weekday}
            monthday={monthday}
            anchorMonth={state.anchorMonth}
            onAnchorMonth={state.setAnchorMonth}
            lookback={lookback}
            lookbackUnit={lookbackUnit}
            onLookbackUnit={changeLookbackUnit}
            onCadence={setCadence}
            onHour={setHour}
            onWeekday={setWeekday}
            onMonthday={setMonthday}
            onLookback={setLookback}
          />
          <SubscriptionCostNote
            cadence={cadence}
            depth={researchMode}
            researching={activeResearch}
          />

          <label className="flex items-start gap-3 text-sm">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 accent-ember"
              checked={state.avoidRepetition}
              onChange={(event) => state.setAvoidRepetition(event.target.checked)}
            />
            <span>
              Prioritise new and changed information
              <span className="mt-1 block text-xs text-muted">
                Compare with previous updates. Retain earlier evidence when needed for context or a
                changed assessment; quiet periods may have no material update.
              </span>
            </span>
          </label>
          {needsQuestion && (
            <div className="border-t border-line pt-5">
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
            </div>
          )}
          <p className="border-t border-line pt-4 text-xs text-muted">
            Saved to {workspaces.label(scope.teamId || null)}.{' '}
            {initial?.enabled === false
              ? 'This subscription remains paused until you resume it.'
              : 'Pause future runs at any time.'}
          </p>
          <Button type="submit" className="w-full min-h-11" busy={busy}>
            {duplicate ? 'Create copy' : initial ? 'Save changes' : 'Create subscription'}
          </Button>
        </aside>
      </fieldset>
    </form>
  );
}
