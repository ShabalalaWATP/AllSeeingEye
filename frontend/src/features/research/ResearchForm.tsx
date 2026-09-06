import { useCallback, useRef, useState, type SyntheticEvent } from 'react';

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
import { FollowUpSummary } from './FollowUpSummary';
import { ResearchProgress } from './ResearchProgress';

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
  const advanced = useRef<HTMLDetailsElement>(null);
  const [question, setQuestion] = useState(initialQuestion);
  const [mode, setMode] = useState<NonNullable<ReportRequest['research_mode']>>(
    parent?.request.research_mode ?? preferences.research_mode,
  );
  const [country, setCountry] = useState(parent?.request.country ?? (parent ? '' : initialCountry));
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
      inputBusy ||
      !template ||
      !ready ||
      (!parent && country !== '' && countriesLoading)
    )
      return;
    const message = !question.trim()
      ? 'Enter a question to research.'
      : question.trim().length > 1000
        ? 'Keep your question within 1,000 characters.'
        : !parent &&
            focus === 'general' &&
            country &&
            !countries.some((item) => item.iso2 === country)
          ? 'Choose an available country or all countries.'
          : selectedLanguages.length === 0
            ? 'Select at least one search language.'
            : (focus === 'company' || focus === 'domain') && !subject.trim()
              ? `Enter a ${focus === 'company' ? 'company name' : 'domain name'}.`
              : privateFocus && !inputId && !parent?.report.version.evidence.length
                ? 'Attach a document or media file before starting this research.'
                : null;
    setValidation(message);
    if (message) {
      if (question.trim() && question.trim().length <= 1000 && advanced.current)
        advanced.current.open = true;
      return;
    }
    const request: ReportRequest = {
      template: template.id,
      question: question.trim(),
      research_mode: mode,
      report_language: reportLanguage,
      report_style: reportStyle,
      research_languages: selectedLanguages,
      research_focus: focus,
      research_subject: focus === 'company' || focus === 'domain' ? subject.trim() : null,
      window_hours: Number(windowHours),
      devils_advocacy: mode === 'detailed',
      ...(focus === 'general' && country ? { country } : {}),
      ...(scope.teamId ? { team_id: scope.teamId } : {}),
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
      className="flex min-w-0 flex-col gap-6"
    >
      <fieldset disabled={action.busy} className="flex min-w-0 flex-col gap-6 disabled:opacity-70">
        <TextAreaField
          label="Your question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          maxLength={1000}
          required
          rows={5}
          placeholder="What has changed, what does it mean, and what should I watch next?"
          className="min-h-40 resize-y bg-surface p-4 text-base leading-relaxed transition-colors focus:border-ember motion-reduce:transition-none"
        />
        <fieldset
          disabled={Boolean(parent)}
          className="grid gap-x-6 gap-y-2 border-b border-line pb-5 sm:grid-cols-2"
        >
          <legend className="mb-2 text-sm font-medium">Research depth</legend>
          {(
            [
              ['quick', 'Quick', 'A focused research run.'],
              [
                'detailed',
                'Detailed',
                'Broader research with a separate challenge to the judgements.',
              ],
            ] as const
          ).map(([value, label, description]) => (
            <label
              key={value}
              className="flex min-h-16 cursor-pointer items-start gap-3 rounded py-3"
            >
              <input
                type="radio"
                name="research-depth"
                value={value}
                checked={mode === value}
                onChange={() => setMode(value)}
                className="mt-1 h-4 w-4 shrink-0 accent-ember"
              />
              <span className="text-sm font-medium">
                {label}
                <span className="mt-1 block text-xs font-normal leading-relaxed text-muted">
                  {description}
                </span>
              </span>
            </label>
          ))}
        </fieldset>
        {parent ? (
          <FollowUpSummary
            parent={parent.report}
            request={parent.request}
            workspaces={workspaces}
          />
        ) : (
          <details ref={advanced} className="min-w-0 border-b border-line pb-4">
            <summary className="cursor-pointer py-2 text-sm font-medium">Scope and sources</summary>
            <p className="mt-1 break-words text-xs text-muted">
              {workspaces.label(scope.teamId)} ·{' '}
              {focus !== 'general'
                ? `${focus} scope`
                : country
                  ? (countries.find((item) => item.iso2 === country)?.name ?? country)
                  : 'All countries'}{' '}
              · {selectedLanguages.length} search{' '}
              {selectedLanguages.length === 1 ? 'language' : 'languages'}
            </p>
            <ResearchScope
              workspaces={workspaces}
              teamId={scope.teamId}
              selectTeam={scope.select}
              countries={countries}
              country={country}
              setCountry={setCountry}
              windowHours={windowHours}
              setWindowHours={setWindowHours}
              selectedLanguages={selectedLanguages}
              setLanguages={setLanguages}
              focus={focus}
              setFocus={(value) => {
                setFocus(value);
                setSubject('');
                setInputId(null);
                if (value !== 'general') setCountry('');
              }}
              subject={subject}
              setSubject={setSubject}
            />
          </details>
        )}
        <ReportOptions
          language={reportLanguage}
          style={reportStyle}
          onLanguage={setReportLanguage}
          onStyle={setReportStyle}
          disabled={Boolean(parent)}
        />
        {privateFocus && (
          <ResearchInput
            key={focus}
            onChange={changeInput}
            onBusyChange={setInputBusy}
            disabled={action.busy}
          />
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
            !template || !ready || inputBusy || (!parent && country !== '' && countriesLoading)
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
