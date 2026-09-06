import { useCallback } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { CopyButton } from '@/components/ui/CopyButton';
import { EvidencePackageDownload } from '@/components/reports/EvidencePackageDownload';
import { ClaimLedgerView } from '@/components/reports/ClaimLedgerView';
import ReportEvidenceMap from '@/components/maps/ReportEvidenceMap';
import { useMapRequest } from '@/components/maps/useMapRequest';
import { localOverlay } from '@/components/maps/savedMapState';
import { parseLocalGeoJson } from '@/lib/map/localGeoJson';
import { fetchMapView } from '@/lib/api/mapViews';
import { ApiError, describeError } from '@/lib/api/errors';
import { deleteReport, fetchReport, regenerateReport } from '@/lib/api/reports';
import { useProfile } from '@/stores/profile';
import { useAuthStore } from '@/stores/auth';
import { formatPersonalDate, formatUtc } from '@/lib/format';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';

import { AdvocacyView, DirectionView, ReportBodyView } from './ReportSections';
import { EvidenceAnnex } from './EvidenceAnnex';
import { EvidenceNavigation } from './EvidenceLinks';
import { ReportReviewStatus } from './ReportReviewStatus';
import { ReportDiff } from './ReportDiff';
import { ReportExports } from './ReportExports';
import { StatusBadge } from './ReportsPage';
import { ReportAssessmentSummary } from './ReportAssessmentSummary';
import { ReportMethodology } from './ReportMethodology';
import { ResearchCoverage } from './ResearchCoverage';
import { CitationCheckMethod } from './CitationChecks';
import { ResearchContextView } from './ResearchContext';
import { ReportChallengeView } from './ReportChallenge';

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
    if (savedMap) {
      savedMap.revision.state.overlays.forEach(localOverlay);
      if (savedMap.revision.state.aoi)
        parseLocalGeoJson(JSON.stringify(savedMap.revision.state.aoi));
    }
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
  const actionError = remove.error ?? regenerate.error;
  return (
    <EvidenceNavigation evidence={version.evidence}>
      <article className="flex h-full min-w-0 flex-col gap-6 overflow-y-auto p-4 sm:p-6">
        <header className="flex flex-col gap-2">
          <Link to="/reports" className="text-xs text-muted hover:underline">
            All reports
          </Link>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-xl font-semibold">{report.title}</h1>
            <StatusBadge status={version.status} />
          </div>
          <p className="font-mono text-xs text-muted">
            {workspaces.label(report.team_id)} · {report.template} ·{' '}
            {version.period_from && version.period_to
              ? `${formatUtc(version.period_from)} to ${formatUtc(version.period_to)}`
              : 'Reporting period unknown for this legacy version'}
          </p>
          <p className="text-xs text-muted">
            Version created: {formatPersonalDate(version.created_at, preferences.profile)}
          </p>
          <ReportReviewStatus status={version.status} />
          <details className="text-xs text-muted">
            <summary className="cursor-pointer">Generation details</summary>
            <p className="mt-2 font-mono">
              {version.model} · {version.attempts} attempt{version.attempts === 1 ? '' : 's'} ·{' '}
              {version.prompt_tokens ?? 'Unknown'} input / {version.completion_tokens ?? 'Unknown'}{' '}
              output tokens · {Math.round(version.latency_ms)} ms
            </p>
            <p className="mt-1">
              Data cut-off: {version.data_cutoff ? formatUtc(version.data_cutoff) : 'Unknown'}
            </p>
          </details>
          <nav aria-label="Versions" className="flex flex-wrap items-center gap-1 text-xs">
            <span className="text-muted">Version</span>
            {versions.map((number) => (
              <Link
                key={number}
                to={`/reports/${id}?version=${String(number)}`}
                aria-current={number === version.number ? 'page' : undefined}
                className={`rounded px-1.5 py-0.5 font-mono ${
                  number === version.number
                    ? 'bg-surface-2 text-text'
                    : 'text-muted hover:text-text'
                }`}
              >
                {number}
              </Link>
            ))}
          </nav>
          {actionError === null ? null : <Alert tone="error">{describeError(actionError)}</Alert>}
        </header>
        {version.status !== 'ready' && (
          <Alert
            tone={version.status === 'failed' ? 'error' : 'warning'}
            title="Validator findings"
          >
            <ul className="list-disc pl-5">
              {version.findings.map((finding, index) => (
                <li key={index}>
                  <span className="font-mono text-xs">{finding.severity}</span> {finding.location}:{' '}
                  {finding.message}
                </li>
              ))}
            </ul>
          </Alert>
        )}
        <ReportBodyView
          body={version.body}
          assessment={version.assessment}
          citationChecks={version.citation_checks}
        />
        <ClaimLedgerView ledger={version.claim_ledger} />
        <ReportEvidenceMap
          key={`${resource.key}:${id}:${String(version.number)}:${mapId}:${mapRevision}`}
          reportId={id}
          version={version.number}
          evidence={version.evidence}
          savedView={data.savedMap}
          scopeLabel={workspaces.label(report.team_id)}
          canCreateView={mapWritable && workspaces.canAcknowledge(report.team_id)}
          canManageView={(view) => mapWritable && workspaces.canManage(view)}
        />
        {version.challenge ? (
          <ReportChallengeView challenge={version.challenge} />
        ) : (
          <AdvocacyView advocacy={version.devils_advocacy} />
        )}
        <Link
          to={`/research?parent=${encodeURIComponent(id)}`}
          className="w-fit rounded border border-line px-4 py-3 text-sm font-medium hover:bg-surface-2"
        >
          Ask a follow-up question
        </Link>
        <section aria-label="Report actions" className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {canEdit && (
              <Button
                variant="secondary"
                busy={regenerate.busy}
                onClick={() => void regenerate.run()}
              >
                Regenerate
              </Button>
            )}
            <CopyButton value={version.markdown} label="Copy Markdown" />
            {canEdit && (
              <Button variant="danger" busy={remove.busy} onClick={() => void remove.run()}>
                Delete
              </Button>
            )}
          </div>
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
          <EvidencePackageDownload
            key={`${id}:${String(version.number)}`}
            id={id}
            version={version.number}
            title={report.title}
          />
        </section>
        <ReportDiff
          key={`${id}:${String(version.number)}`}
          id={id}
          current={version.number}
          latest={report.latest_version}
        />
        <ResearchCoverage receipt={version.research} />
        <ResearchContextView context={version.research_context} />
        <CitationCheckMethod checks={version.citation_checks} />
        <ReportAssessmentSummary assessment={version.assessment} />
        <ReportMethodology savedMethod={version.assessment?.method_version} />
        <DirectionView direction={version.direction} />
        <EvidenceAnnex
          evidence={version.evidence}
          findings={version.findings}
          status={version.status}
          assessment={version.assessment}
        />
      </article>
    </EvidenceNavigation>
  );
}
