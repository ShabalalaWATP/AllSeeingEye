import { researchDateError } from './ResearchTimeScope';
import { ProjectHistory, projectInterval, type ProjectHistoryState } from './ProjectHistory';
import { useState, type SyntheticEvent } from 'react';
import { Link } from 'react-router';
import type { SavedMapView } from '@/lib/api/mapViews';
import type { Profile } from '@/lib/api/profile';
import { describeError } from '@/lib/api/errors';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextAreaField, TextField } from '@/components/ui/Field';
import { ResearchDepth } from '@/components/research/ResearchDepth';
import { ReportOptions } from '@/components/reports/ReportOptions';
import { useAuthStore } from '@/stores/auth';
import { ResearchPlanEditor } from './ResearchPlanEditor';
import { ResearchProgress } from './ResearchProgress';
import { useResearchPlan } from './useResearchPlan';
import { useResearchRun } from './useResearchRun';

export function AreaResearchForm({
  saved,
  preferences,
  workspaces,
}: {
  saved: SavedMapView;
  preferences: Profile;
  workspaces: Workspaces;
}) {
  const user = useAuthStore((state) => state.user);
  const [question, setQuestion] = useState('');
  const [since, setSince] = useState('');
  const [until, setUntil] = useState('');
  const [history, setHistory] = useState<ProjectHistoryState>({
    enabled: false,
    firstYear: '2000',
    lastYear: '2021',
  });
  const historical = history.enabled;
  const years = historical ? projectInterval(history) : null;
  const fixedSince = historical ? (years?.since ?? '') : since ? `${since}Z` : '';
  const fixedUntil = historical ? (years?.until ?? '') : until ? `${until}Z` : '';
  const [mode, setMode] = useState(preferences.research_mode);
  const [language, setLanguage] = useState(preferences.report_language);
  const [style, setStyle] = useState(preferences.report_style);
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const action = useResearchRun();
  const teamId = saved.view.team_id;
  const plan = useResearchPlan({
    question,
    ...(historical
      ? { history: { since: fixedSince, until: fixedUntil, projectId: history.projectId ?? '' } }
      : {}),
    windowHours: '',
    languages: preferences.research_languages,
    mode,
    focus: 'general',
    subject: '',
    country: '',
    area: {
      viewId: saved.view.id,
      revisionId: saved.revision.id,
      teamId,
      since: fixedSince,
      until: fixedUntil,
    },
  });
  const writable =
    !workspaces.loading &&
    workspaces.canAcknowledge(teamId) &&
    (teamId === null ||
      user?.role === 'admin' ||
      workspaces.teams.some((entry) => entry.team.id === teamId && entry.team.is_active)) &&
    (teamId !== null || user?.id === saved.view.created_by);
  const eligible =
    plan.current &&
    plan.snapshot?.tasks.some(
      (task) =>
        task.selected &&
        task.supported &&
        task.spatial_supported &&
        (!historical || task.source_id === 'research-aiddata-projects'),
    );
  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (action.busy || plan.busy || !writable) return;
    const duration = Date.parse(fixedUntil) - Date.parse(fixedSince);
    const message = !question.trim()
      ? 'Enter a research question.'
      : !Number.isFinite(duration) ||
          duration <= 0 ||
          duration > (historical ? 10980 : 730) * 86_400_000
        ? historical
          ? 'Choose valid project years spanning at most 30 years.'
          : 'Choose a positive UTC interval of at most two years (730 days).'
        : !historical && researchDateError({ since: fixedSince, until: fixedUntil })
          ? researchDateError({ since: fixedSince, until: fixedUntil })
          : !eligible
            ? 'Preview this area and interval with at least one supported selected source.'
            : !consent
              ? 'Confirm disclosure of the area and interval before collection.'
              : null;
    setError(message);
    if (message) return;
    void action.run({
      ...plan.request,
      template: 'ask',
      question: question.trim(),
      research_mode: mode,
      research_web_search: false,
      research_focus: 'general',
      research_languages: preferences.research_languages,
      report_language: language,
      report_style: style,
      devils_advocacy: mode !== 'quick',
      team_id: teamId,
      map_view_id: saved.view.id,
      map_revision_id: saved.revision.id,
      research_since: fixedSince,
      research_until: fixedUntil,
      ...(historical ? { research_time_basis: 'recorded_time' as const } : {}),
      disclose_area_to_provider: true,
    });
  };
  return (
    <form aria-label="Research a saved area" onSubmit={submit} className="space-y-6">
      <div className="border-l-2 border-ember pl-4">
        <h2 className="text-lg font-semibold">{saved.revision.title}</h2>
        <p className="text-sm text-muted">
          Saved map revision {saved.revision.number}, report version{' '}
          {saved.revision.report_version_number}. Save to {workspaces.label(teamId)}.
        </p>
        <p className="mt-2 text-xs text-muted">
          Research uses this saved area. Parent evidence and local overlays are not collected
          automatically.
        </p>
      </div>
      <Link
        className="inline-block text-sm text-ember underline"
        to={`/research?brief=new&map_view=${encodeURIComponent(saved.view.id)}&map_revision=${encodeURIComponent(saved.revision.id)}&question=${encodeURIComponent(question)}`}
      >
        Use this area and question in a Research Brief
      </Link>
      <fieldset disabled={action.busy || !writable} className="space-y-5">
        <TextAreaField
          label="Your area research question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          maxLength={1000}
          required
          rows={4}
        />
        <ProjectHistory
          value={history}
          onChange={(value) => {
            setHistory(value);
            setConsent(false);
          }}
        />
        {!historical && (
          <>
            <div className="grid gap-4 sm:grid-cols-2">
              <TextField
                label="Acquisition / publication from (UTC)"
                type="datetime-local"
                step="1"
                value={since}
                onChange={(e) => {
                  setSince(e.target.value);
                  setConsent(false);
                }}
                required
              />
              <TextField
                label="Acquisition / publication until (UTC, exclusive)"
                type="datetime-local"
                step="1"
                value={until}
                onChange={(e) => {
                  setUntil(e.target.value);
                  setConsent(false);
                }}
                required
              />
            </div>
            <p className="text-xs text-muted">
              At most two years (730 days), subject to each source’s archive limits. The start is
              included and the end excluded. Observations use acquisition time; other reporting uses
              publication time. Map display filters are not copied into this collection interval.
            </p>
          </>
        )}
        <ResearchDepth value={mode} onChange={setMode} />
        <ResearchPlanEditor plan={plan} languages={preferences.research_languages} area />
        <ReportOptions
          language={language}
          style={style}
          onLanguage={setLanguage}
          onStyle={setStyle}
        />
        <label className="flex gap-3 text-sm">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
          Allow selected providers to receive this area and interval for collection.
        </label>
        <Button type="submit" disabled={!eligible || !consent || plan.busy} busy={action.busy}>
          Research saved area
        </Button>
      </fieldset>
      {!writable && (
        <Alert tone="warning">
          This saved area's ownership or team permissions do not allow a new report in this scope.
        </Alert>
      )}
      {error && <Alert tone="error">{error}</Alert>}
      {action.error && <Alert tone="error">{describeError(action.error)}</Alert>}
      <ResearchProgress
        snapshot={action.progress.snapshot}
        active={action.progress.active}
        onCancel={action.progress.cancel}
        onRetry={() => void action.retry()}
      />
    </form>
  );
}
