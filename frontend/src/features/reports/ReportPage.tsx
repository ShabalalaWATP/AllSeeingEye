import { useCallback, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';

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

import { EvidenceNavigation } from './EvidenceLinks';
import { LegacyReportReferences } from './LegacyReportReferences';
import { ReportExports } from './ReportExports';
import { ReportPublicationView, publicationContents } from './ReportPublication';
import { ReportReviewStatus } from './ReportReviewStatus';
import { ReportBodyView } from './ReportSections';
import { ReportWorkspaceDrawer } from './ReportWorkspaceDrawer';
import './reportReader.css';

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
  const remove = useAsyncAction(async () => {
    await deleteReport(id);
    await navigate('/reports');
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
  const canEdit = workspaces.canManage(report);
  const mapWritable =
    actor?.role === 'admin' ||
    !report.team_id ||
    workspaces.teams.some((entry) => entry.team.id === report.team_id && entry.team.is_active);
  const versions = Array.from({ length: report.latest_version }, (_, index) => index + 1);
  const contents = version.publication ? publicationContents(version.publication) : [];
  const period =
    version.period_from && version.period_to
      ? `${formatUtc(version.period_from)} to ${formatUtc(version.period_to)}`
      : 'Reporting period unknown for this legacy version';
  const actionError = remove.error ?? regenerate.error;
  return (
    <EvidenceNavigation evidence={version.evidence}>
      <section
        aria-label="Report reader"
        className="report-reader-shell h-full min-w-0 overflow-y-auto"
      >
        <div className="report-reader-frame px-3 py-4 sm:px-6 sm:py-6">
          <header className="mb-5 flex flex-col gap-4 border-b border-line pb-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-3">
                <Link
                  to="/reports"
                  className="rounded px-2 py-2 text-sm text-muted transition-colors hover:bg-surface hover:text-text motion-reduce:transition-none"
                >
                  ← Reports
                </Link>
                <span className="hidden h-4 w-px bg-line sm:block" aria-hidden="true" />
                <p className="truncate text-xs text-muted">
                  {workspaces.label(report.team_id)} · Version {version.number}
                </p>
              </div>
              <div className="flex items-center gap-2">
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
                />
              </div>
            </div>
            <p className="font-mono text-[11px] leading-5 text-muted">
              {period} · Version created:{' '}
              {formatPersonalDate(version.created_at, preferences.profile)}
            </p>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <ReportReviewStatus status={version.status} />
              <nav aria-label="Versions" className="flex flex-wrap items-center gap-1 text-xs">
                <span className="mr-1 text-muted">Versions</span>
                {versions.map((number) => (
                  <Link
                    key={number}
                    to={`/reports/${id}?version=${String(number)}`}
                    aria-current={number === version.number ? 'page' : undefined}
                    className={`rounded px-2 py-1 font-mono transition-colors motion-reduce:transition-none ${
                      number === version.number
                        ? 'bg-surface-2 text-text'
                        : 'text-muted hover:text-text'
                    }`}
                  >
                    {number}
                  </Link>
                ))}
              </nav>
            </div>
          </header>

          <div
            className={contents.length ? 'lg:grid lg:grid-cols-[13rem_minmax(0,1fr)] lg:gap-8' : ''}
          >
            {contents.length > 0 && (
              <aside className="hidden lg:block" aria-label="Report contents">
                <nav className="sticky top-6 border-l border-line pl-4">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">
                    Contents
                  </p>
                  <ol className="mt-3 space-y-2.5 text-xs leading-5 text-muted">
                    {contents.map((entry, index) => (
                      <li key={entry.id}>
                        <a className="transition-colors hover:text-text" href={`#${entry.id}`}>
                          <span className="mr-2 font-mono text-[10px] text-ember">
                            {String(index + 1).padStart(2, '0')}
                          </span>
                          {entry.label}
                        </a>
                      </li>
                    ))}
                  </ol>
                </nav>
              </aside>
            )}
            <article className="report-reader-paper report-reader-enter min-w-0 overflow-hidden rounded-card">
              <div className="report-reader-content">
                {version.publication ? (
                  <ReportPublicationView publication={version.publication} />
                ) : (
                  <>
                    <h1 className="text-[clamp(2rem,5vw,3.25rem)] font-semibold leading-[1.05] tracking-[-0.045em] text-[#171512]">
                      {report.title}
                    </h1>
                    <ReportBodyView body={version.body} />
                    {!workspaceOpen && <LegacyReportReferences evidence={version.evidence} />}
                  </>
                )}
              </div>
            </article>
          </div>

          <footer className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-5 text-xs text-muted">
            <span>
              {version.evidence.length} retained source item
              {version.evidence.length === 1 ? '' : 's'} · Exact version {version.number}
            </span>
            <Link
              to={version.research?.plan?.area ? '/' : `/research?parent=${encodeURIComponent(id)}`}
              className="rounded px-3 py-2 text-sm font-medium text-text transition-colors hover:bg-surface-2 motion-reduce:transition-none"
            >
              {version.research?.plan?.area
                ? 'Research another map area →'
                : 'Ask a follow-up question →'}
            </Link>
          </footer>
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
