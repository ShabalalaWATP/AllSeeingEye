import { lazy, Suspense, useEffect, useState, type MouseEvent, type ReactNode } from 'react';

import { ClaimAnnotations } from '@/components/reports/ClaimAnnotations';
import { ClaimExportSelection } from '@/components/reports/ClaimExportSelection';
import { ClaimLedgerView } from '@/components/reports/ClaimLedgerView';
import { EvidencePackageDownload } from '@/components/reports/EvidencePackageDownload';
import { IdentityReviews } from '@/components/reports/IdentityReviews';
import { OriginalAssets } from '@/components/reports/OriginalAssets';
import { RelationshipReviews } from '@/components/reports/RelationshipReviews';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import type { SavedMapView } from '@/lib/api/mapViews';
import type { ReportSummary, ReportVersion } from '@/lib/api/reports';
import { formatUtc } from '@/lib/format';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';
import { useAuthStore } from '@/stores/auth';

import { AnnotationMonitorsSection } from './AnnotationMonitorsSection';
import { AssessmentReview } from './AssessmentReview';
import { DirectionView } from './ReportSections';
import { EvidenceAnnex } from './EvidenceAnnex';
import { FreshWebContext } from './FreshWebContext';
import { ReportAssessmentSummary } from './ReportAssessmentSummary';
import { ReportChallengeView } from './ReportChallenge';
import { ReportDiff } from './ReportDiff';
import { ReportManagement } from './ReportManagement';
import { ReportMethodology } from './ReportMethodology';
import { AdvocacyView } from './ReportSections';
import { ReportedRelationships } from './ReportedRelationships';
import { ResearchContextView } from './ResearchContext';
import { ResearchCoverage } from './ResearchCoverage';
import { ReviewedSnapshots } from './ReviewedSnapshots';
import { reviewerName } from './reviewerNames';
import type { SourceReviewContext } from './SourceReviewPanel';

const ReportEvidenceMap = lazy(() => import('@/components/maps/ReportEvidenceMap'));

type WorkspaceView = 'sources' | 'analysis' | 'collection' | 'map' | 'review';

const views: [WorkspaceView, string][] = [
  ['sources', 'Sources'],
  ['analysis', 'Assessment'],
  ['collection', 'Collection'],
  ['map', 'Evidence map'],
  ['review', 'Review'],
];

/** A visited view stays mounted while hidden; an unvisited one has not loaded anything yet. */
function ViewPanel({
  id,
  view,
  visited,
  children,
}: {
  id: WorkspaceView;
  view: WorkspaceView;
  visited: ReadonlySet<WorkspaceView>;
  children: ReactNode;
}) {
  if (!visited.has(id)) return null;
  return (
    <div hidden={view !== id} className="space-y-8">
      {children}
    </div>
  );
}

export interface ReportSupportingWorkspaceProps {
  reportId: string;
  report: ReportSummary;
  version: ReportVersion;
  savedMap?: SavedMapView | undefined;
  workspaces: Workspaces;
  canEdit: boolean;
  mapWritable: boolean;
  actionError: string | null;
  regenerating: boolean;
  deleting: boolean;
  onRegenerate: () => void;
  onDelete: () => void;
}

export default function ReportSupportingWorkspace({
  reportId,
  report,
  version,
  savedMap,
  workspaces,
  canEdit,
  mapWritable,
  actionError,
  regenerating,
  deleting,
  onRegenerate,
  onDelete,
}: ReportSupportingWorkspaceProps) {
  // A refused action reloads the report under fresh access; reopen where its error and retry live.
  const [view, setView] = useState<WorkspaceView>(() => (actionError ? 'review' : 'sources'));
  // Views stay mounted once visited, so unsaved editor input survives switching between them.
  const [visited, setVisited] = useState<ReadonlySet<WorkspaceView>>(() => new Set([view]));
  const [shownError, setShownError] = useState(actionError);
  const show = (next: WorkspaceView) => {
    setView(next);
    setVisited((current) => (current.has(next) ? current : new Set(current).add(next)));
  };
  if (actionError !== shownError) {
    // Adjusting state while rendering: a new action error opens the view that explains it.
    setShownError(actionError);
    if (actionError) show('review');
  }
  const panel = (id: WorkspaceView) => ({ id, view, visited });
  const [pendingEvidenceId, setPendingEvidenceId] = useState<string | null>(null);
  const canAcknowledge = mapWritable && workspaces.canAcknowledge(report.team_id);
  const actorId = useAuthStore((state) => state.user?.id);
  const reviewer = (id: string) => reviewerName(id, actorId, workspaces.teams);
  const sourceReview: SourceReviewContext = {
    reportId,
    version: version.number,
    judgements: version.body.key_judgements,
    canWrite: canEdit && mapWritable,
    scopeLabel: workspaces.label(report.team_id),
    reviewer,
  };
  useEffect(() => {
    if (view !== 'sources' || !pendingEvidenceId) return;
    const target = document.getElementById(pendingEvidenceId);
    if (!(target instanceof HTMLDetailsElement)) return;
    target.open = true;
    const scrollIntoView: unknown = Reflect.get(target, 'scrollIntoView');
    if (typeof scrollIntoView === 'function') scrollIntoView.call(target, { block: 'start' });
    target.querySelector('summary')?.focus({ preventScroll: true });
  }, [pendingEvidenceId, view]);

  const showCitedEvidence = (event: MouseEvent<HTMLDivElement>) => {
    if (view === 'sources' || !(event.target instanceof Element)) return;
    const link = event.target.closest<HTMLAnchorElement>('a[href^="#evidence-"]');
    if (!link) return;
    event.preventDefault();
    event.stopPropagation();
    setPendingEvidenceId(decodeURIComponent(link.hash.slice(1)));
    show('sources');
  };
  return (
    <div className="min-w-0" onClickCapture={showCitedEvidence}>
      <nav
        aria-label="Supporting report views"
        className="sticky top-0 z-10 -mx-5 flex gap-1 overflow-x-auto border-b border-line bg-surface px-5 pb-3 sm:-mx-7 sm:px-7"
      >
        {views.map(([id, label]) => (
          <button
            key={id}
            type="button"
            aria-current={view === id ? 'page' : undefined}
            className={`shrink-0 rounded px-3 py-2 text-sm transition-colors motion-reduce:transition-none ${
              view === id ? 'bg-surface-2 text-text' : 'text-muted hover:text-text'
            }`}
            onClick={() => show(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      {/* Keeps focused or cited content below the sticky view bar when scrolled into view. */}
      <div className="mt-6 space-y-8 [&_*]:scroll-mt-16">
        <ViewPanel {...panel('sources')}>
          <EvidenceAnnex
            evidence={version.evidence}
            findings={version.findings}
            status={version.status}
            assessment={version.assessment}
            review={sourceReview}
          />
          <ReviewedSnapshots
            key={`snapshots:${reportId}:${String(version.number)}`}
            reportId={reportId}
            version={version.number}
            title={report.title}
            judgements={version.body.key_judgements}
            canWrite={sourceReview.canWrite}
            reviewer={reviewer}
          />
          <ClaimLedgerView ledger={version.claim_ledger} />
          <OriginalAssets
            reportId={reportId}
            version={version.number}
            evidence={version.evidence}
            canEdit={canEdit}
          />
          <EvidencePackageDownload
            key={`${reportId}:${String(version.number)}`}
            id={reportId}
            version={version.number}
            title={report.title}
          />
        </ViewPanel>

        <ViewPanel {...panel('analysis')}>
          <ReportMethodology savedMethod={version.assessment?.method_version} />
          <ReportAssessmentSummary assessment={version.assessment} />
          <AssessmentReview reportId={reportId} version={version} teams={workspaces.teams} />
          {version.challenge ? (
            <ReportChallengeView challenge={version.challenge} />
          ) : (
            <AdvocacyView advocacy={version.devils_advocacy} />
          )}
          <ResearchContextView context={version.research_context} />
          <ReportedRelationships evidence={version.evidence} />
          <DirectionView direction={version.direction} />
        </ViewPanel>

        <ViewPanel {...panel('collection')}>
          <ResearchCoverage receipt={version.research} />
          <FreshWebContext record={version.research?.web_research} />
        </ViewPanel>

        <ViewPanel {...panel('map')}>
          <Suspense fallback={<LoadingNote label="Loading evidence map" />}>
            <ReportEvidenceMap
              key={`${reportId}:${String(version.number)}:${savedMap?.revision.id ?? ''}`}
              reportId={reportId}
              version={version.number}
              initialTimeBasis={version.research?.time_basis ?? 'publication'}
              initialResearchArea={version.research?.plan?.area ?? null}
              evidence={version.evidence}
              savedView={savedMap}
              scopeLabel={workspaces.label(report.team_id)}
              canCreateView={canAcknowledge}
              canManageView={(savedView) => mapWritable && workspaces.canManage(savedView)}
            />
          </Suspense>
        </ViewPanel>

        <ViewPanel {...panel('review')}>
          <ClaimExportSelection reportId={reportId} version={version.number}>
            <div className="space-y-8">
              {actionError && <Alert tone="error">{actionError}</Alert>}
              {version.status !== 'ready' && (
                <Alert
                  tone={version.status === 'failed' ? 'error' : 'warning'}
                  title="Review findings"
                >
                  <ul className="mt-1 list-disc space-y-1 pl-5">
                    {version.findings.map((finding, index) => (
                      <li key={index}>
                        {finding.location}: {finding.message}
                      </li>
                    ))}
                  </ul>
                </Alert>
              )}
              <details className="border-b border-line pb-6 text-xs text-muted">
                <summary className="w-fit cursor-pointer rounded py-2 font-medium text-text focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember">
                  Generation details
                </summary>
                <p className="mt-2 font-mono leading-5">
                  {version.model} · {version.attempts} attempt
                  {version.attempts === 1 ? '' : 's'} · {version.prompt_tokens ?? 'Unknown'} input /{' '}
                  {version.completion_tokens ?? 'Unknown'} output tokens ·{' '}
                  {Math.round(version.latency_ms)} ms
                </p>
                <p className="mt-1">
                  Data cut-off: {version.data_cutoff ? formatUtc(version.data_cutoff) : 'Unknown'}
                </p>
              </details>
              {canEdit && (
                <ReportManagement
                  title={report.title}
                  workspaceLabel={workspaces.label(report.team_id)}
                  versions={report.latest_version}
                  actionError={actionError}
                  regenerating={regenerating}
                  deleting={deleting}
                  onRegenerate={onRegenerate}
                  onDelete={onDelete}
                />
              )}
              <ClaimAnnotations
                sharedSelection
                key={`claims:${reportId}:${version.number}`}
                reportId={reportId}
                version={version.number}
                evidence={version.evidence}
                canCreate={canAcknowledge}
                generation={version.claim_generation}
                canManage={(root) => mapWritable && workspaces.canManage(root)}
              />
              <IdentityReviews
                reportId={reportId}
                version={version.number}
                subject={
                  report.scope.research_focus === 'company' &&
                  typeof report.scope.research_subject === 'string'
                    ? report.scope.research_subject
                    : null
                }
                candidates={version.research_context?.identity_candidates ?? []}
                evidence={version.evidence}
                canCreate={canAcknowledge}
                canManage={(root) => mapWritable && workspaces.canManage(root)}
              />
              <RelationshipReviews
                reportId={reportId}
                version={version.number}
                evidence={version.evidence}
                canCreate={canAcknowledge}
                canManage={(root) => mapWritable && workspaces.canManage(root)}
              />
              <AnnotationMonitorsSection
                reportId={reportId}
                version={version.number}
                canCreate={canAcknowledge}
              />
              <ReportDiff
                key={`diff:${reportId}:${String(version.number)}`}
                id={reportId}
                current={version.number}
                latest={report.latest_version}
              />
            </div>
          </ClaimExportSelection>
        </ViewPanel>
      </div>
    </div>
  );
}
