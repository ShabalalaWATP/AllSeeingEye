import { projectInterval, type ProjectHistoryState } from './ProjectHistory';
import { useCallback, useState, type SyntheticEvent } from 'react';

import type { Profile } from '@/lib/api/profile';
import { ReportOptions } from '@/components/reports/ReportOptions';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextAreaField } from '@/components/ui/Field';
import type { Country } from '@/lib/api/geoSchemas';
import type { Report, ReportRequest, ReportTemplate } from '@/lib/api/reports';
import { describeError } from '@/lib/api/errors';
import { useWorkspaceSelection, type Workspaces } from '@/lib/hooks/useWorkspaces';

import { ResearchScope, type ResearchFocus } from './ResearchScope';
import { useResearchRun } from './useResearchRun';
import { ResearchInput } from './ResearchInput';
import { DocumentResearchInput } from './DocumentResearchInput';
import { FollowUpSummary } from './FollowUpSummary';
import { ResearchProgress } from './ResearchProgress';
import { ResearchPlanEditor } from './ResearchPlanEditor';
import { useResearchPlan } from './useResearchPlan';
import { recordScopeError } from './recordScope';
import { ResearchDepth } from './ResearchDepth';
import { MAX_RESEARCH_HOURS, researchDateError, type ResearchDates } from './ResearchTimeScope';

export function ResearchForm({
  preferences,
  workspaces,
  countries,
  countriesLoading,
  template,
  initialQuestion,
  initialCountry,
  parent,
}: {
  preferences: Profile;
  workspaces: Workspaces;
  countries: readonly Country[];
  countriesLoading: boolean;
  template: ReportTemplate | undefined;
  initialQuestion: string;
  initialCountry: string;
  parent?: { report: Report; request: ReportRequest } | undefined;
}) {
  const scope = useWorkspaceSelection(workspaces);
  const action = useResearchRun();
  const { clearError } = action;
  const [question, setQuestion] = useState(initialQuestion);
  const [mode, setMode] = useState<NonNullable<ReportRequest['research_mode']>>(
    parent?.request.research_mode ?? preferences.research_mode,
  );
  const [selectedCountries, setCountries] = useState<string[]>(
    parent?.request.countries ??
      (parent?.request.country
        ? [parent.request.country]
        : !parent && initialCountry
          ? [initialCountry]
          : []),
  );
  const [dates, setDates] = useState<ResearchDates | null>(
    parent?.request.research_since && parent.request.research_until
      ? { since: parent.request.research_since, until: parent.request.research_until }
      : null,
  );
  const [webSearch, setWebSearch] = useState(parent?.request.research_web_search ?? false);
  const [windowHours, setWindowHours] = useState(
    String(parent?.request.window_hours ?? preferences.research_window_days * 24),
  );
  const [selectedLanguages, setLanguages] = useState(
    parent?.request.research_languages ?? preferences.research_languages,
  );
  const [reportLanguage, setReportLanguage] = useState<
    NonNullable<ReportRequest['report_language']>
  >(parent?.request.report_language ?? preferences.report_language);
  const [reportStyle, setReportStyle] = useState<NonNullable<ReportRequest['report_style']>>(
    parent?.request.report_style ?? preferences.report_style,
  );
  const [focus, setFocus] = useState<ResearchFocus>(parent?.request.research_focus ?? 'general');
  const [subject, setSubject] = useState(parent?.request.research_subject ?? '');
  const [history, setHistory] = useState<ProjectHistoryState>({
    enabled: false,
    firstYear: '2000',
    lastYear: '2021',
  });
  const historical = !parent && focus === 'general' && history.enabled;
  const interval = historical ? projectInterval(history) : null;
  const collectionPlan = useResearchPlan({
    ...(historical
      ? {
          history: {
            ...(interval ?? { since: '', until: '' }),
            projectId: history.projectId ?? '',
          },
        }
      : {}),
    question,
    windowHours,
    languages: selectedLanguages,
    mode,
    focus,
    subject,
    countries: focus === 'general' ? selectedCountries : [],
    ...(dates && !historical ? { dates } : {}),
    webSearch: webSearch && !['document', 'media'].includes(focus),
  });
  const [validation, setValidation] = useState<string | null>(null);
  const [inputId, setInputId] = useState<string | null>(null);
  const [inputBusy, setInputBusy] = useState(false);
  const changeInput = useCallback(
    (id: string | null) => {
      setInputId(id);
      setValidation(null);
      clearError();
    },
    [clearError],
  );
  const privateFocus = focus === 'document' || focus === 'media';
  const teamId = parent ? (parent.report.report.team_id ?? '') : scope.teamId;
  const ready = parent
    ? !workspaces.loading && (!teamId || workspaces.teams.some((entry) => entry.team.id === teamId))
    : scope.ready;

  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (
      action.busy ||
      collectionPlan.busy ||
      inputBusy ||
      !template ||
      !ready ||
      (!parent && selectedCountries.length > 0 && countriesLoading)
    )
      return;
    const message = !question.trim()
      ? 'Enter a question to research.'
      : question.trim().length > 1000
        ? 'Keep your question within 1,000 characters.'
        : !parent &&
            focus === 'general' &&
            (selectedCountries.length > 8 ||
              selectedCountries.some((code) => !countries.some((item) => item.iso2 === code)))
          ? 'Choose up to eight available countries, or use worldwide.'
          : selectedLanguages.length === 0
            ? 'Select at least one search language.'
            : (focus === 'company' || focus === 'domain') && !subject.trim()
              ? `Enter a ${focus === 'company' ? 'company name' : 'domain name'}.`
              : privateFocus && !inputId && !parent?.report.version.evidence.length
                ? 'Attach a document or media file before starting this research.'
                : !parent && !privateFocus && collectionPlan.customised && !collectionPlan.current
                  ? 'Preview your edited collection plan before starting research.'
                  : null;
    const scopeError =
      message ??
      (!parent && !historical
        ? dates
          ? researchDateError(dates)
          : !Number.isInteger(Number(windowHours)) ||
              Number(windowHours) <= 0 ||
              Number(windowHours) > MAX_RESEARCH_HOURS
            ? 'Choose a valid search period of up to two years.'
            : null
        : null) ??
      (historical &&
      (!interval ||
        !collectionPlan.current ||
        !collectionPlan.snapshot?.tasks.some(
          (task) =>
            task.source_id === 'research-aiddata-projects' && task.selected && task.supported,
        ))
        ? 'Choose valid project years and preview a supported selected source.'
        : null) ??
      (!parent && focus === 'general' ? recordScopeError(subject.trim(), selectedCountries) : null);
    setValidation(scopeError);
    if (scopeError) return;
    const request: ReportRequest = {
      disclose_area_to_provider: false,
      template: template.id,
      question: question.trim(),
      research_mode: mode,
      report_language: reportLanguage,
      report_style: reportStyle,
      research_languages: selectedLanguages,
      research_focus: focus,
      research_subject: !privateFocus && subject.trim() ? subject.trim() : null,
      ...(historical
        ? {
            research_since: interval?.since ?? null,
            research_until: interval?.until ?? null,
            research_time_basis: 'recorded_time' as const,
          }
        : dates
          ? { research_since: dates.since, research_until: dates.until }
          : { window_hours: Number(windowHours) }),
      devils_advocacy: mode === 'detailed',
      ...(focus === 'general' ? { countries: selectedCountries } : {}),
      research_web_search: !privateFocus && webSearch,
      ...(scope.teamId ? { team_id: scope.teamId } : {}),
      ...(!parent && !privateFocus ? collectionPlan.request : {}),
      ...parent?.request,
      ...(privateFocus && inputId ? { research_input_id: inputId } : {}),
    };
    void action.run(request);
  };

  return (
    <form
      aria-label="Research a question"
      onSubmit={submit}
      noValidate
      className="flex min-w-0 flex-col gap-5"
    >
      <fieldset disabled={action.busy} className="flex min-w-0 flex-col gap-5 disabled:opacity-70">
        <TextAreaField
          label="Your question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          maxLength={1000}
          required
          rows={3}
          placeholder="What has changed, what does it mean, and what should I watch next?"
          className="min-h-28 resize-y bg-surface p-4 text-base leading-relaxed transition-colors focus:border-ember motion-reduce:transition-none"
        />
        <ResearchDepth value={mode} onChange={setMode} disabled={Boolean(parent)} />
        {parent ? (
          <FollowUpSummary
            parent={parent.report}
            request={parent.request}
            workspaces={workspaces}
          />
        ) : (
          <section aria-label="Scope and sources" className="min-w-0 border-b border-line pb-5">
            <h2 className="text-sm font-medium">Scope and sources</h2>
            <ResearchScope
              history={history}
              setHistory={setHistory}
              workspaces={workspaces}
              teamId={scope.teamId}
              selectTeam={scope.select}
              countries={countries}
              selectedCountries={selectedCountries}
              setCountries={setCountries}
              dates={dates}
              setDates={setDates}
              webSearch={webSearch}
              setWebSearch={setWebSearch}
              windowHours={windowHours}
              setWindowHours={setWindowHours}
              selectedLanguages={selectedLanguages}
              setLanguages={setLanguages}
              focus={focus}
              setFocus={(value) => {
                setFocus(value);
                setSubject('');
                setInputId(null);
                if (value === 'document' || value === 'media') setWebSearch(false);
                if (value !== 'general') {
                  setCountries([]);
                  setHistory((previous) => ({ ...previous, enabled: false }));
                }
              }}
              subject={subject}
              setSubject={setSubject}
            />
          </section>
        )}
        {!parent && !privateFocus && (
          <ResearchPlanEditor
            plan={collectionPlan}
            languages={selectedLanguages}
            historical={historical}
            fixed={Boolean(dates)}
          />
        )}
        <ReportOptions
          language={reportLanguage}
          style={reportStyle}
          onLanguage={setReportLanguage}
          onStyle={setReportStyle}
          disabled={Boolean(parent)}
        />
        {focus === 'document' ? (
          <DocumentResearchInput
            key={`${focus}:${teamId}`}
            onChange={changeInput}
            onBusyChange={setInputBusy}
            disabled={action.busy}
          />
        ) : (
          privateFocus && (
            <ResearchInput
              key={`${focus}:${teamId}`}
              onChange={changeInput}
              onBusyChange={setInputBusy}
              disabled={action.busy}
            />
          )
        )}
      </fieldset>
      {!scope.valid && (
        <Alert tone="error">
          This team is no longer available. Choose Personal or another team.
        </Alert>
      )}
      {validation && <Alert tone="error">{validation}</Alert>}
      {action.error && <Alert tone="error">{describeError(action.error)}</Alert>}
      <div className="flex flex-wrap items-center gap-4">
        <Button
          type="submit"
          className="min-h-12 px-6"
          busy={action.busy}
          disabled={
            !template ||
            !ready ||
            collectionPlan.busy ||
            inputBusy ||
            (!parent && selectedCountries.length > 0 && countriesLoading)
          }
        >
          Start research
        </Button>
        <span className="text-xs text-muted">Save to {workspaces.label(teamId)}</span>
      </div>
      <ResearchProgress
        snapshot={action.progress.snapshot}
        active={action.progress.active}
        onCancel={action.progress.cancel}
      />
    </form>
  );
}
