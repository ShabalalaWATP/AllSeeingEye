import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { ApiError, describeError } from '@/lib/api/errors';
import { fetchMapView } from '@/lib/api/mapViews';
import { deleteReport, fetchReport, regenerateReport } from '@/lib/api/reports';
import { formatPersonalDate, formatUtc } from '@/lib/format';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useMapRequest } from '@/components/maps/useMapRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';
import { useAuthStore } from '@/stores/auth';
import { useProfile } from '@/stores/profile';
import {
  launchAssistantReportQuestion,
  registerAssistantReportContext,
} from '@/lib/assistantReportContext';
import { followUpAvailability } from '@/features/research/followUpScope';

import { EvidenceNavigation } from './EvidenceLinks';
import { LegacyReportReferences } from './LegacyReportReferences';
import { MobileReportContents, ReportContentsRail } from './ReportContentsNav';
import { ReportExports } from './ReportExports';
import { ReportMasthead } from './ReportMasthead';
import { ReportPageFooter } from './ReportPageFooter';
import { ReportPublicationView, publicationContents } from './ReportPublication';
import { ReportReviewStatus } from './ReportReviewStatus';
import { ReportBodyView } from './ReportSections';
import { ReportWorkspaceDrawer } from './ReportWorkspaceDrawer';
import './reportReader.css';
import { savedPathFor } from './savedReportOrigin';

function versionFromQuery(value: string | null): number | undefined {
  const parsed = Number(value);
  return value !== null && Number.isInteger(parsed) && parsed >= 1 ? parsed : undefined;
}

export default function ReportPage() {
  const workspaces = useWorkspaces();
  const preferences = useProfile();
  const actor = useAuthStore((state) => state.user);
  const { id = '' } = useParams();
  const [params] = useSearchParams();
  const requested = versionFromQuery(params.get('version'));
  const mapId = params.get('map_view');
  const mapRevision = params.get('map_revision');
  const mapRequest = useMapRequest();
  const navigate = useNavigate();
  const [workspaceOpen, setWorkspaceOpen] = useState(false);
  const closeWorkspace = useCallback(() => setWorkspaceOpen(false), []);
  const loader = useCallback(async () => {
    const signal = mapRequest();
    const savedMap =
      mapId && mapRevision ? await fetchMapView(mapId, mapRevision, signal) : undefined;
    if (
      (mapId || mapRevision) &&
      (!savedMap ||
        !requested ||
        savedMap.view.report_id !== id ||
        savedMap.revision.report_version_number !== requested)
    )
      throw new ApiError(
        422,
        'invalid_map_link',
        'This map link must identify its exact report version and immutable revision.',
      );
    signal.throwIfAborted();
    const report = await fetchReport(id, requested, signal);
    signal.throwIfAborted();
    return { ...report, savedMap };
  }, [id, requested, mapId, mapRevision, mapRequest]);
  const resource = useScopedResource(loader);
  const { data, error, loading, reload } = resource;
  const eyeReport = useMemo(
    () =>
      data
        ? {
            id: data.report.id,
            version: data.version.number,
            title: data.report.title,
            dataCutoff: data.version.data_cutoff ?? null,
          }
        : null,
    [data],
  );
  useEffect(() => (eyeReport ? registerAssistantReportContext(eyeReport) : undefined), [eyeReport]);
  const remove = useAsyncAction(async () => {
    await deleteReport(id);
    // Back to the section that holds this kind of report.
    await navigate(savedPathFor(data?.report));
  });
  const regenerate = useAsyncAction(async () => {
    await regenerateReport(id);
    await navigate(`/reports/${id}`);
    await reload();
  });

  if (data === null) {
    return (
      <section className="p-6">
        {error === null ? null : <Alert tone="error">{describeError(error)}</Alert>}
        {loading ? <LoadingNote label="Loading report" /> : null}
      </section>
    );
  }
  const { report, version } = data;
  const followUp = followUpAvailability({ report, version });
  const canEdit = workspaces.canManage(report);
  const mapWritable =
    actor?.role === 'admin' ||
    !report.team_id ||
    workspaces.teams.some((entry) => entry.team.id === report.team_id && entry.team.is_active);
  const contents = version.publication ? publicationContents(version.publication) : [];
  const period =
    version.period_from && version.period_to
      ? `${formatUtc(version.period_from)} to ${formatUtc(version.period_to)}`
      : 'Unknown for this legacy version';
  const actionError = remove.error ?? regenerate.error;
  return (
    <EvidenceNavigation evidence={version.evidence}>
      <section
        aria-label="Report reader"
        className="report-reader-shell h-full min-w-0 overflow-y-auto"
      >
        <div className="report-reader-frame px-3 py-4 sm:px-6 sm:py-6">
          <ReportMasthead
            reportId={id}
            workspaceLabel={workspaces.label(report.team_id)}
            version={version.number}
            latestVersion={report.latest_version}
            period={period}
            createdLabel={formatPersonalDate(version.created_at, preferences.profile)}
            actions={
              <>
                <button
                  type="button"
                  className="rounded-md border border-cyan/50 bg-cyan/10 px-3 py-2 text-sm font-medium text-text transition-colors hover:bg-cyan/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan motion-reduce:transition-none"
                  onClick={() => eyeReport && launchAssistantReportQuestion(eyeReport)}
                >
                  Ask Eye about this version
                </button>
                <button
                  type="button"
                  className="rounded-md border border-line px-3 py-2 text-sm font-medium text-text transition-colors hover:bg-surface-2 motion-reduce:transition-none"
                  onClick={() => setWorkspaceOpen(true)}
                >
                  Sources &amp; methods
                </button>
                <ReportExports
                  language={
                    typeof report.scope.report_language === 'string'
                      ? report.scope.report_language
                      : undefined
                  }
                  preferred={preferences.profile?.export_format ?? 'pdf'}
                  id={id}
                  version={version.number}
                  title={report.title}
                  status={version.status}
                />
              </>
            }
          />

          <MobileReportContents contents={contents} />

          <div
            className={contents.length ? 'lg:grid lg:grid-cols-[13rem_minmax(0,1fr)] lg:gap-8' : ''}
          >
            <ReportContentsRail contents={contents} />
            <article className="report-reader-paper report-reader-enter min-w-0 overflow-hidden rounded-card">
              <div className="report-reader-content">
                {version.publication ? (
                  <ReportPublicationView
                    publication={version.publication}
                    status={version.status}
                  />
                ) : (
                  <>
                    <header className="report-reader-masthead">
                      <p className="report-reader-eyebrow">Research report</p>
                      <h1 className="report-reader-title">{report.title}</h1>
                      <div className="mt-4">
                        <ReportReviewStatus status={version.status} variant="paper" />
                      </div>
                    </header>
                    <ReportBodyView body={version.body} />
                    {!workspaceOpen && <LegacyReportReferences evidence={version.evidence} />}
                  </>
                )}
              </div>
            </article>
          </div>

          <ReportPageFooter reportId={id} version={version} followUp={followUp} />
        </div>
      </section>
      <ReportWorkspaceDrawer
        open={workspaceOpen}
        onClose={closeWorkspace}
        workspace={{
          reportId: id,
          report,
          version,
          savedMap: data.savedMap,
          workspaces,
          canEdit,
          mapWritable,
          actionError: actionError ? describeError(actionError) : null,
          regenerating: regenerate.busy,
          deleting: remove.busy,
          onRegenerate: () => void regenerate.run(),
          onDelete: () => void remove.run(),
        }}
      />
    </EvidenceNavigation>
  );
}
