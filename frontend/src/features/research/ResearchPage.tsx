import { Link, useSearchParams } from 'react-router';
import { useCallback } from 'react';
import { useProfile } from '@/stores/profile';
import { ResearchNavigation } from '@/components/research/ResearchNavigation';
import { BriefWorkspace } from '@/components/research/BriefWorkspace';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { ApiError, describeError } from '@/lib/api/errors';
import { fetchCountries } from '@/lib/api/geo';
import { fetchReport, fetchTemplates } from '@/lib/api/reports';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';
import { readResearchDraftDates } from '@/lib/researchNavigation';

import { SavedAreaResearch } from './SavedAreaResearch';
import { ResearchForm } from './ResearchForm';
import { followUpAvailability } from '@/lib/followUpScope';

function versionFromQuery(value: string | null): number | undefined {
  if (value === null || !/^[1-9]\d*$/.test(value)) return undefined;
  const version = Number(value);
  return Number.isSafeInteger(version) ? version : undefined;
}

export default function ResearchPage() {
  const [params] = useSearchParams();
  const workspaces = useWorkspaces();
  const preferences = useProfile();
  const templates = useScopedResource(fetchTemplates);
  const countries = useScopedResource(fetchCountries);
  const parentId = params.get('parent');
  const requestedVersionText = params.get('parent_version');
  const requestedVersion = versionFromQuery(requestedVersionText);
  const invalidParentLink =
    (requestedVersionText !== null && (requestedVersion === undefined || !parentId)) ||
    (parentId !== null && parentId.length === 0);
  const areaRequested = params.has('map_view') || params.has('map_revision');
  const briefId = params.get('brief');
  const briefRevision = versionFromQuery(params.get('revision'));
  const fromReportVersion = versionFromQuery(params.get('from_report_version'));
  const invalidBriefLink = Boolean(
    briefId &&
    ((params.has('revision') && briefRevision === undefined) ||
      (params.has('from_report') && (!params.get('from_report') || !fromReportVersion)) ||
      (params.has('from_report_version') && !params.has('from_report'))),
  );
  const loadParent = useCallback(async () => {
    if (!parentId || invalidParentLink) return null;
    const report = await fetchReport(parentId, requestedVersion);
    if (requestedVersion !== undefined && report.version.number !== requestedVersion)
      throw new ApiError(
        422,
        'invalid_parent_version',
        'The selected parent edition could not be loaded.',
      );
    return { report, ...followUpAvailability(report) };
  }, [parentId, requestedVersion, invalidParentLink]);
  const parent = useScopedResource(loadParent);
  const template = templates.data?.find((item) => item.id === 'ask' && item.needs_question);
  return (
    <section className="h-full min-w-0 overflow-y-auto px-4 py-8 sm:px-8">
      <div className="mx-auto flex max-w-4xl flex-col gap-5">
        <header>
          <h1 className="text-3xl font-semibold tracking-tight">Research</h1>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-muted">
            Ask a question, choose your scope and collect an answer from the available sources. Save
            the findings with their evidence and uncertainty.
          </p>
        </header>
        <ResearchNavigation />
        {!briefId && (
          <div className="flex flex-wrap gap-4 text-sm">
            <Link className="text-ember underline" to="/research?brief=new">
              Create a Research Brief
            </Link>
            <Link className="text-text underline" to="/research?brief=library">
              My briefs
            </Link>
            {areaRequested && !parentId && (
              <Link
                className="text-text underline"
                to={`/research?brief=new&map_view=${encodeURIComponent(params.get('map_view') ?? '')}&map_revision=${encodeURIComponent(params.get('map_revision') ?? '')}`}
              >
                Use saved map in a brief
              </Link>
            )}
          </div>
        )}
        {invalidBriefLink && (
          <Alert tone="error">Choose an exact Research Brief and report edition.</Alert>
        )}
        {briefId && !invalidBriefLink && (
          <BriefWorkspace
            briefId={briefId}
            revision={briefRevision}
            initialQuestion={params.get('question') ?? undefined}
            mapViewId={params.get('map_view') ?? undefined}
            mapRevisionId={params.get('map_revision') ?? undefined}
            fromReportId={params.get('from_report') ?? undefined}
            fromReportVersion={fromReportVersion}
            intent={params.get('intent') === 'subscribe' ? 'subscribe' : undefined}
          />
        )}
        {!briefId && (
          <>
            {templates.loading && <LoadingNote label="Loading research options" />}
            {countries.loading && params.get('country') && (
              <LoadingNote label="Loading country scope" />
            )}
            {templates.error && (
              <div className="space-y-3">
                <Alert tone="error">{describeError(templates.error)}</Alert>
                <Button variant="secondary" onClick={() => void templates.reload()}>
                  Retry research options
                </Button>
              </div>
            )}
            {!templates.loading && !templates.error && !template && (
              <Alert tone="warning">
                Question research is unavailable because the Ask the Eye product is not configured.
              </Alert>
            )}
            {countries.error && (
              <p className="text-xs text-muted">
                Country choices could not be loaded.{' '}
                <button
                  type="button"
                  className="text-ember underline"
                  onClick={() => void countries.reload()}
                >
                  Retry countries
                </button>
              </p>
            )}
            {parentId && parent.loading && (
              <LoadingNote label="Loading the saved follow-up scope" />
            )}
            {invalidParentLink && (
              <Alert tone="error">
                This follow-up link needs a valid parent report and edition.
              </Alert>
            )}
            {parentId && parent.error && (
              <Alert tone="error">
                {describeError(parent.error)}{' '}
                <Button variant="secondary" onClick={() => void parent.reload()}>
                  Retry parent report
                </Button>
              </Alert>
            )}
            {parent.data?.reason && (
              <Alert tone="warning">
                Follow-up unavailable: {parent.data.reason} Start a new research question with an
                explicit scope if you need to change the period or area.
              </Alert>
            )}
            {!preferences.profile && !preferences.error && (
              <LoadingNote label="Loading your research defaults" />
            )}
            {preferences.error && !preferences.profile && (
              <Alert tone="error">
                Research defaults could not be loaded.{' '}
                <Button variant="secondary" onClick={() => void preferences.reload()}>
                  Retry preferences
                </Button>
              </Alert>
            )}
            {areaRequested && parentId && (
              <Alert tone="error">Choose area research or a parent follow-up, not both.</Alert>
            )}
            {areaRequested && !parentId && preferences.profile && (
              <SavedAreaResearch
                viewId={params.get('map_view') ?? ''}
                revisionId={params.get('map_revision') ?? ''}
                preferences={preferences.profile}
                workspaces={workspaces}
              />
            )}
            {!areaRequested &&
              !invalidParentLink &&
              preferences.profile &&
              (!parentId ||
                (parent.data?.report.report.id === parentId && parent.data.request !== null)) && (
                <ResearchForm
                  key={`${workspaces.key}:${params.toString()}:${parent.data?.report.version.number ?? ''}`}
                  preferences={preferences.profile}
                  workspaces={workspaces}
                  countries={countries.data ?? []}
                  countriesLoading={countries.loading}
                  template={template}
                  initialQuestion={params.get('question') ?? ''}
                  initialDates={readResearchDraftDates(params)}
                  initialCountry={(
                    params.get('country') ??
                    preferences.profile.research_country ??
                    ''
                  ).toUpperCase()}
                  parent={parentId && parent.data?.request ? parent.data : undefined}
                />
              )}
          </>
        )}
        <footer className="flex flex-col gap-3 pb-4 text-xs leading-relaxed text-muted">
          <p>
            Automated research can be incomplete or mistaken. Inspect the cited evidence and
            confidence limits before relying on a judgement.
          </p>
          <Link to="/reports" className="w-fit py-2 text-text underline underline-offset-4">
            View saved reports
          </Link>
        </footer>
      </div>
    </section>
  );
}
