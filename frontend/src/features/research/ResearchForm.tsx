/**
 * One column, read top to bottom in the order a person decides: what to ask, how deep to
 * go, where to look, which themes, which conflict or disaster, what to read and which
 * period. The rarely changed settings sit folded at the end, before the start button.
 */
import { useCallback, useState, type SyntheticEvent } from 'react';

import { ReportOptions } from '@/components/reports/ReportOptions';
import { ChipPicker } from '@/components/research/ChipPicker';
import { CountryMultiSelect } from '@/components/research/CountryMultiSelect';
import { FocusPicker } from '@/components/research/FocusPicker';
import { Step, Toggle } from '@/components/research/FormStep';
import { ResearchDepth } from '@/components/research/ResearchDepth';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextAreaField } from '@/components/ui/Field';
import { describeError } from '@/lib/api/errors';
import type { Country } from '@/lib/api/geoSchemas';
import type { Profile } from '@/lib/api/profile';
import type { ReportTemplate } from '@/lib/api/reports';
import { useWorkspaceSelection, type Workspaces } from '@/lib/hooks/useWorkspaces';
import { MAX_REGIONS, REGIONS } from '@/lib/regions';
import type { ResearchDates } from '@/lib/researchPeriod';
import { MAX_THEMES, THEMES } from '@/lib/themes';

import { DocumentResearchInput } from './DocumentResearchInput';
import { FollowUpSummary } from './FollowUpSummary';
import { projectInterval } from './ProjectHistory';
import { ResearchFocusField } from './ResearchFocusField';
import { ResearchInput } from './ResearchInput';
import { ResearchPlanEditor } from './ResearchPlanEditor';
import { ResearchProgress } from './ResearchProgress';
import {
  initialDraft,
  isPrivateFocus,
  researchIssue,
  researchRequest,
  type Parent,
  type ResearchDraft,
  type ResearchFocus,
} from './researchRequest';
import { ResearchScope } from './ResearchScope';
import { ResearchTimeScope } from './ResearchTimeScope';
import { useResearchPlan } from './useResearchPlan';
import { useResearchRun } from './useResearchRun';

export function ResearchForm({
  preferences,
  workspaces,
  countries,
  countriesLoading,
  template,
  initialQuestion,
  initialDates,
  initialCountry,
  parent,
}: {
  preferences: Profile;
  workspaces: Workspaces;
  countries: readonly Country[];
  countriesLoading: boolean;
  template: ReportTemplate | undefined;
  initialQuestion: string;
  initialDates?: ResearchDates | null;
  initialCountry: string;
  parent?: Parent | undefined;
}) {
  const scope = useWorkspaceSelection(workspaces);
  const action = useResearchRun();
  const { clearError } = action;
  const [draft, setDraft] = useState<ResearchDraft>(() =>
    initialDraft(preferences, parent, initialQuestion, initialDates, initialCountry),
  );
  const patch = (changes: Partial<ResearchDraft>) =>
    setDraft((current) => ({ ...current, ...changes }));
  const [validation, setValidation] = useState<string | null>(null);
  const [inputBusy, setInputBusy] = useState(false);
  const changeInput = useCallback(
    (inputId: string | null) => {
      setDraft((current) => ({ ...current, inputId }));
      setValidation(null);
      clearError();
    },
    [clearError],
  );
  const { focus } = draft;
  const privateFocus = isPrivateFocus(focus);
  const general = focus === 'general';
  const historical = !parent && general && draft.history.enabled;
  const interval = historical ? projectInterval(draft.history) : null;
  const plan = useResearchPlan({
    ...(historical
      ? {
          history: {
            ...(interval ?? { since: '', until: '' }),
            projectId: draft.history.projectId ?? '',
          },
        }
      : {}),
    question: draft.question,
    windowHours: draft.windowHours,
    languages: draft.languages,
    mode: draft.mode,
    focus,
    subject: draft.subject,
    countries: general ? draft.countries : [],
    ...(draft.dates && !historical ? { dates: draft.dates } : {}),
    webSearch: draft.webSearch && !privateFocus,
  });
  const teamId = parent ? (parent.report.report.team_id ?? '') : scope.teamId;
  const ready = parent
    ? !workspaces.loading && (!teamId || workspaces.teams.some((entry) => entry.team.id === teamId))
    : scope.ready;
  const waiting =
    !template ||
    !ready ||
    plan.busy ||
    inputBusy ||
    (!parent && draft.countries.length > 0 && countriesLoading);
  const changeFocus = (value: ResearchFocus) =>
    patch({
      focus: value,
      subject: '',
      inputId: null,
      ...(isPrivateFocus(value) ? { webSearch: false } : {}),
      ...(value !== 'general'
        ? {
            countries: [],
            regions: [],
            conflictId: '',
            hazard: '',
            history: { ...draft.history, enabled: false },
          }
        : {}),
    });
  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (action.busy || waiting) return;
    const ctx = { parent, countries, historical, interval, plan };
    const issue = researchIssue(draft, ctx);
    setValidation(issue);
    if (issue) return;
    void action.run(researchRequest(draft, ctx, template, scope.teamId));
  };
  let step = 0;
  const next = () => ++step;
  const showRead = privateFocus || !parent;

  return (
    <form
      aria-label="Research a question"
      onSubmit={submit}
      noValidate
      className="flex min-w-0 flex-col gap-5"
    >
      <fieldset disabled={action.busy} className="grid min-w-0 gap-10 disabled:opacity-70">
        <Step
          number={next()}
          title="What to ask"
          lead="Any topic: a conflict, a market, an organisation, a technology or a place."
          id="research-question"
        >
          <TextAreaField
            label="Your question"
            value={draft.question}
            onChange={(event) => patch({ question: event.target.value })}
            maxLength={1000}
            required
            rows={3}
            placeholder="What has changed, what does it mean, and what should I watch next?"
            className="min-h-28 resize-y bg-surface p-4 text-base leading-relaxed transition-colors focus:border-ember motion-reduce:transition-none"
          />
          {!parent && (
            <ResearchFocusField
              focus={focus}
              subject={draft.subject}
              onFocus={changeFocus}
              onSubject={(subject) => patch({ subject })}
            />
          )}
        </Step>

        <Step number={next()} title="How deep to go" id="research-depth">
          <ResearchDepth
            value={draft.mode}
            onChange={(mode) => patch({ mode })}
            disabled={Boolean(parent)}
          />
        </Step>

        {parent && (
          <FollowUpSummary
            parent={parent.report}
            request={parent.request}
            workspaces={workspaces}
          />
        )}

        {!parent && general && (
          <Step
            number={next()}
            title="Where to look"
            lead="Choose regions, nations, or both. Leave both empty for the whole world."
            id="research-countries"
          >
            <ChipPicker
              label="Regions"
              options={REGIONS}
              value={draft.regions}
              onChange={(regions) => patch({ regions })}
              max={MAX_REGIONS}
            />
            <CountryMultiSelect
              label="Nations"
              countries={countries}
              value={draft.countries}
              onChange={(value) => patch({ countries: value })}
            />
          </Step>
        )}

        {!parent && !privateFocus && (
          <Step
            number={next()}
            title="Which themes"
            lead="Narrow the evidence to the kinds of reporting that matter. None means all of it."
            id="research-themes"
          >
            <ChipPicker
              label="Themes"
              options={THEMES}
              value={draft.themes}
              onChange={(themes) => patch({ themes })}
              max={MAX_THEMES}
            />
          </Step>
        )}

        {!parent && general && (
          <Step
            number={next()}
            title="Conflict or disaster"
            lead="Optional. Pin the question to one tracked conflict or one kind of hazard."
            id="research-focus"
          >
            <FocusPicker
              conflictId={draft.conflictId}
              hazard={draft.hazard}
              onChange={(choice) => patch(choice)}
            />
          </Step>
        )}

        {showRead && (
          <Step
            number={next()}
            title="What to read"
            lead={
              privateFocus
                ? 'Private input research stays within your selected AI connection. Public web search is disabled for attachments.'
                : 'The live evidence the app already collects for your scope is always read.'
            }
            id="research-sources"
          >
            {!privateFocus && (
              <Toggle
                checked={draft.webSearch}
                onChange={(webSearch) => patch({ webSearch })}
                title="Fresh web search"
                detail="Also ask the selected AI search provider to search the public web using your question, countries and dates. Results are combined with app sources and linked in the report. Requires a compatible, configured AI connection."
              >
                {draft.webSearch && (
                  <span className="mt-2 block text-xs text-ember">
                    Your question and scope will be sent to that provider. Search results may have
                    incomplete dates or geographic coverage.
                  </span>
                )}
              </Toggle>
            )}
            {focus === 'document' && (
              <DocumentResearchInput
                key={`${focus}:${teamId}`}
                onChange={changeInput}
                onBusyChange={setInputBusy}
                disabled={action.busy}
              />
            )}
            {focus === 'media' && (
              <ResearchInput
                key={`${focus}:${teamId}`}
                onChange={changeInput}
                onBusyChange={setInputBusy}
                disabled={action.busy}
              />
            )}
          </Step>
        )}

        {!parent && !historical && (
          <Step
            number={next()}
            title="Which period"
            lead="How far back the sources are searched."
            id="research-period"
          >
            <ResearchTimeScope
              windowHours={draft.windowHours}
              setWindowHours={(windowHours) => patch({ windowHours })}
              dates={draft.dates}
              setDates={(dates) => patch({ dates })}
            />
          </Step>
        )}

        {!parent && (
          <Step
            number={next()}
            title="Scope and sources"
            lead="Where the report is saved, which languages are read, and the finer source settings."
            id="research-scope"
          >
            <ResearchScope
              history={draft.history}
              setHistory={(history) => patch({ history })}
              workspaces={workspaces}
              teamId={scope.teamId}
              selectTeam={scope.select}
              countries={countries}
              selectedCountries={draft.countries}
              setCountries={(value) => patch({ countries: value })}
              selectedLanguages={draft.languages}
              setLanguages={(languages) => patch({ languages })}
              focus={focus}
              subject={draft.subject}
              setSubject={(subject) => patch({ subject })}
            />
            {!privateFocus && (
              <ResearchPlanEditor
                plan={plan}
                languages={draft.languages}
                historical={historical}
                fixed={Boolean(draft.dates)}
              />
            )}
          </Step>
        )}

        <ReportOptions
          language={draft.reportLanguage}
          style={draft.reportStyle}
          onLanguage={(reportLanguage) => patch({ reportLanguage })}
          onStyle={(reportStyle) => patch({ reportStyle })}
          disabled={Boolean(parent)}
        />
      </fieldset>
      {!scope.valid && (
        <Alert tone="error">
          This team is no longer available. Choose Personal or another team.
        </Alert>
      )}
      {validation && <Alert tone="error">{validation}</Alert>}
      {action.error && <Alert tone="error">{describeError(action.error)}</Alert>}
      <div className="flex flex-wrap items-center gap-4 border-t border-line pt-6">
        <Button type="submit" className="min-h-12 px-6" busy={action.busy} disabled={waiting}>
          Start research
        </Button>
        <span className="text-xs text-muted">Save to {workspaces.label(teamId)}</span>
      </div>
      <ResearchProgress
        snapshot={action.progress.snapshot}
        active={action.progress.active}
        onCancel={action.progress.cancel}
        onRetry={() => void action.retry()}
      />
    </form>
  );
}
