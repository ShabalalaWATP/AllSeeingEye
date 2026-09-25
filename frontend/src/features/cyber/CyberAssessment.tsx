import { Link } from 'react-router';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import type { CyberDays } from '@/lib/api/cyber';
import { formatUtc } from '@/lib/format';
import { briefingKeyPoints, briefingLead } from './cyberBriefingModel';
import type { CyberBriefingState } from './useCyberWorkspace';

/** The AI executive picture, kept at the top of the page rather than behind a tab. */
export function CyberAssessment({ state, days }: { state: CyberBriefingState; days: CyberDays }) {
  const { briefing, report, error, loading, retry } = state;
  const job = briefing?.job;
  const pending = job?.status === 'queued' || job?.status === 'running';
  const lead = report ? briefingLead(report) : null;
  const points = report ? briefingKeyPoints(report) : [];
  return (
    <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
      <article
        aria-label="AI assessment"
        className="rounded-xl border border-cyan/30 bg-[linear-gradient(135deg,color-mix(in_srgb,var(--color-cyan)_10%,var(--color-surface)),var(--color-surface))] p-5 sm:p-6"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="font-mono text-2xs tracking-[0.22em] text-cyan uppercase">
            {days}-day AI assessment
          </p>
          {briefing && (
            <p className="text-[11px] text-muted">
              Period {formatUtc(briefing.period_from)} to {formatUtc(briefing.period_to)}
            </p>
          )}
        </div>
        {loading && !briefing && (
          <p role="status" className="mt-4 text-sm text-muted">
            Loading your cyber assessment…
          </p>
        )}
        {error && (
          <Alert tone="error" className="mt-4">
            {describeError(error)}{' '}
            <Button variant="ghost" onClick={retry}>
              Retry cyber briefing
            </Button>
          </Alert>
        )}
        {pending && (
          <div role="status" className="mt-4 space-y-3">
            <p className="text-sm leading-6">
              Collecting cyber evidence and writing the assessment. Research continues on the
              server; the page updates when it completes.
            </p>
            {job.total_sections > 0 && (
              <progress
                aria-label="Cyber briefing sections completed"
                value={job.completed_sections}
                max={job.total_sections}
                className="h-1 w-full max-w-lg accent-ember"
              />
            )}
          </div>
        )}
        {job && !pending && !report && !error && (
          <Alert tone="warning" className="mt-4">
            {job.status === 'paused'
              ? 'The cyber briefing is paused.'
              : 'The cyber briefing could not be completed.'}{' '}
            <Link className="text-ember underline" to={`/research/jobs/${job.id}`}>
              Review cyber research progress
            </Link>
          </Alert>
        )}
        {report && (
          <div className="mt-4 space-y-4">
            {report.version.status !== 'ready' && (
              <p className="border-l-2 border-amber pl-3 text-xs leading-5 text-amber">
                This briefing needs review before it is relied on.
              </p>
            )}
            {lead ? (
              <p className="max-w-[70ch] text-base leading-7">{lead.text}</p>
            ) : (
              <p className="text-sm leading-6 text-muted">
                There is not enough evidence for an overall cyber assessment in this period.
              </p>
            )}
            {points.length > 0 && (
              <ul className="max-w-[70ch] list-disc space-y-2 pl-5 text-sm leading-6 marker:text-ember">
                {points.map((point) => (
                  <li key={point.text}>{point.text}</li>
                ))}
              </ul>
            )}
            <div className="flex flex-wrap gap-4 text-xs">
              <a href="#cyber-briefing" className="text-ember hover:underline">
                Read the full cited briefing
              </a>
              {job?.report_id && (
                <Link to={`/reports/${job.report_id}`} className="text-ember hover:underline">
                  Open saved report and exports
                </Link>
              )}
            </div>
          </div>
        )}
      </article>
      <aside
        aria-label="How to read this workspace"
        className="rounded-xl border border-line/70 bg-surface/60 p-5 text-xs leading-6 text-muted"
      >
        <h3 className="text-sm font-semibold text-text">How to read this page</h3>
        <ul className="mt-3 space-y-2">
          <li>
            <span className="text-text">Lenses</span> are keyword and metadata matches over
            headlines. They point at reporting; they never attribute an incident.
          </li>
          <li>
            <span className="text-text">State associations</span> repeat the wording of the MITRE
            ATT&CK profile for a mentioned group. A mention is a research lead, not proof.
          </li>
          <li>
            <span className="text-text">Ransomware claims</span> are criminal statements relayed by
            an aggregator. <span className="text-text">Connectivity signals</span> are measurements
            without a cause.
          </li>
          <li>
            The <span className="text-text">GNSS map</span> is an aircraft-accuracy proxy for
            roughly the last day. It does not locate a transmitter or confirm intent.
          </li>
        </ul>
        {briefing && (
          <p className="mt-4 border-t border-line/60 pt-3">
            Assessment reused for 24 hours. Next refresh {formatUtc(briefing.next_refresh_at)}.
          </p>
        )}
      </aside>
    </div>
  );
}
