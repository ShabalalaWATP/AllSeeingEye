/**
 * One column, read top to bottom in the order a person decides: what to call it, what to
 * ask, how deep to go, where to look, which themes, which conflict or disaster, whether
 * to search the web, and finally when. The rarely changed settings sit folded at the end.
 */
import { useRef, useState, type SyntheticEvent } from 'react';

import { ChipPicker } from '@/components/research/ChipPicker';
import { CountryMultiSelect } from '@/components/research/CountryMultiSelect';
import { Step, Toggle } from '@/components/research/FormStep';
import { ResearchDepth } from '@/components/research/ResearchDepth';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField, TextField } from '@/components/ui/Field';
import type { Country } from '@/lib/api/geoSchemas';
import { MAX_REGIONS, REGIONS } from '@/lib/regions';
import { MAX_THEMES, THEMES } from '@/lib/themes';

import { focusScheduleIssue, scheduleIssueTarget } from './scheduleFormFocus';
import { ScheduleFocus } from './ScheduleFocus';
import { ScheduleScope } from './ScheduleScope';
import { ScheduleTiming } from './ScheduleTiming';
import { SubscriptionCostNote } from './SubscriptionCostNote';
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
  const { needsQuestion, activeResearch, subjectScoped, boundaryScoped, product } = state;
  const validateSubmit = (event: SyntheticEvent<HTMLFormElement>) => {
    if (state.invalid) {
      event.preventDefault();
      setAttempted(true);
      if (state.issues[0]) focusScheduleIssue(form.current, state.issues[0]);
      return;
    }
    state.submit(event);
  };
  let step = 0;
  const next = () => ++step;
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
      <header className="mb-8 flex items-start justify-between gap-4">
        <div>
          <p className="mb-2 font-mono text-2xs tracking-[0.22em] text-cyan uppercase">
            {duplicate ? 'Copy' : initial ? 'Edit' : 'New'}
          </p>
          <h2 tabIndex={-1} className="text-2xl font-semibold tracking-tight">
            {duplicate
              ? 'Duplicate subscription'
              : initial
                ? 'Edit subscription'
                : 'Create a subscription'}
          </h2>
          <p className="mt-2 max-w-xl text-sm text-muted">
            Name it, ask it, scope it, then say when. Each run arrives as a cited report that leads
            with what changed.
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
      <fieldset disabled={busy} className="mx-auto grid max-w-3xl gap-10 disabled:opacity-70">
        {state.invalidPlan && (
          <Alert tone="error">
            The linked plan is no longer available. Choose a plan in this workspace or select No
            plan.
          </Alert>
        )}

        <Step number={next()} title="What to call it" id="subscription-name">
          <TextField
            label="Subscription name"
            error={attempted && !state.name.trim() ? 'Enter a subscription name.' : undefined}
            value={state.name}
            onChange={(event) => state.setName(event.target.value)}
            required
            maxLength={120}
            placeholder="Weekly energy developments"
          />
        </Step>

        {needsQuestion && (
          <Step
            number={next()}
            title="What to follow"
            lead="Any topic: a conflict, a market, an organisation, a technology or a place."
            id="subscription-question"
          >
            <TextAreaField
              label="Question"
              error={
                attempted && state.issues.some((issue) => issue.field === 'Question')
                  ? 'Enter a question.'
                  : undefined
              }
              value={state.question}
              onChange={(event) => state.setQuestion(event.target.value)}
              rows={3}
              className="min-h-28 resize-y bg-surface p-4 text-base leading-relaxed"
              maxLength={1000}
              required={!state.selectedPlan || activeResearch}
              placeholder="What has changed, what is supported by evidence, and what should I watch next?"
            />
          </Step>
        )}

        {needsQuestion && (
          <Step number={next()} title="How deep to go" id="subscription-depth">
            <ResearchDepth value={state.researchMode} onChange={state.setResearchMode} />
          </Step>
        )}

        <Step
          number={next()}
          title="Where to look"
          lead={
            subjectScoped
              ? 'This focused search follows its organisation or domain rather than a place.'
              : boundaryScoped
                ? 'A boundary drawn on the map sets the place for this subscription.'
                : 'Choose regions, nations, or both. Leave both empty for the whole world.'
          }
          id="subscription-countries"
        >
          {product?.needs_country ? (
            <SelectField
              label="Nation"
              value={state.countriesInScope[0] ?? ''}
              onChange={(event) =>
                state.setCountries(event.target.value ? [event.target.value] : [])
              }
              options={[
                { value: '', label: 'Choose one nation' },
                ...countries.map((item) => ({ value: item.iso2, label: item.name })),
              ]}
            />
          ) : (
            <>
              <div id="subscription-regions">
                <ChipPicker
                  label="Regions"
                  options={REGIONS}
                  value={state.regions}
                  onChange={state.setRegions}
                  max={MAX_REGIONS}
                  disabled={subjectScoped || boundaryScoped}
                />
              </div>
              <CountryMultiSelect
                label="Nations"
                countries={countries}
                value={state.countriesInScope}
                onChange={state.setCountries}
                disabled={subjectScoped || boundaryScoped}
              />
            </>
          )}
        </Step>

        {needsQuestion && (
          <Step
            number={next()}
            title="Which themes"
            lead="Narrow the evidence to the kinds of reporting that matter. None means all of it."
            id="subscription-themes"
          >
            <ChipPicker
              label="Themes"
              options={THEMES}
              value={state.themes}
              onChange={state.setThemes}
              max={MAX_THEMES}
            />
          </Step>
        )}

        {needsQuestion && !subjectScoped && (
          <Step
            number={next()}
            title="Conflict or disaster"
            lead="Optional. Pin the subscription to one tracked conflict or one kind of hazard."
            id="subscription-coverage"
          >
            <ScheduleFocus
              conflictId={state.conflictId}
              hazard={state.hazard}
              hasBoundary={Boolean(state.researchArea)}
              discloseArea={state.discloseArea}
              onEventFocus={state.changeEventFocus}
              onClearBoundary={state.clearBoundary}
              onDiscloseArea={state.setDiscloseArea}
            />
          </Step>
        )}

        {activeResearch && (
          <Step
            number={next()}
            title="What to read"
            lead="Every run reads the live evidence the app already collects for your scope."
            id="subscription-sources"
          >
            <Toggle
              checked={state.webSearch}
              onChange={state.setWebSearch}
              title="Also search the web each run"
              detail="Uses the workspace connection where supported. Provider usage may incur charges."
            />
          </Step>
        )}

        <Step
          number={next()}
          title="When to run"
          lead="Updates appear in Saved updates as complete reports with citations and exports."
          id="subscription-timing"
        >
          <ScheduleTiming
            cadence={state.cadence}
            hour={state.hour}
            weekday={state.weekday}
            monthday={state.monthday}
            anchorMonth={state.anchorMonth}
            onAnchorMonth={state.setAnchorMonth}
            lookback={state.lookback}
            lookbackUnit={state.lookbackUnit}
            onLookbackUnit={state.changeLookbackUnit}
            onCadence={state.setCadence}
            onHour={state.setHour}
            onWeekday={state.setWeekday}
            onMonthday={state.setMonthday}
            onLookback={state.setLookback}
          />
          <SubscriptionCostNote
            cadence={state.cadence}
            depth={state.researchMode}
            researching={activeResearch}
          />
          <Toggle
            checked={state.avoidRepetition}
            onChange={state.setAvoidRepetition}
            title="Prioritise new and changed information"
            detail="Compare with previous updates. Earlier evidence is kept when it explains a change; a quiet period may bring no material update."
          />
          {needsQuestion && (
            <Toggle
              checked={state.notifyOnChange}
              onChange={state.setNotifyOnChange}
              title="Notify in app when evidence changes"
              detail="The first report sets the baseline. Later runs compare evidence and assessments; an alert is not verification."
            />
          )}
        </Step>

        <ScheduleScope
          state={state}
          workspaces={workspaces}
          templates={templates}
          initial={Boolean(initial)}
        />

        <div className="flex flex-wrap items-center justify-between gap-4 border-t border-line pt-6">
          <p className="text-xs text-muted">
            Saved to {workspaces.label(state.scope.teamId || null)}.{' '}
            {initial?.enabled === false
              ? 'This subscription remains paused until you resume it.'
              : 'Pause future runs at any time.'}
          </p>
          <Button type="submit" className="min-h-11 min-w-48" busy={busy}>
            {duplicate ? 'Create copy' : initial ? 'Save changes' : 'Create subscription'}
          </Button>
        </div>
      </fieldset>
    </form>
  );
}
