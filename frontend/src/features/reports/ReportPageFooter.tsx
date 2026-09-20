import { Link } from 'react-router';

import type { ReportVersion } from '@/lib/api/reports';
import type { followUpAvailability } from '@/lib/followUpScope';

const action =
  'rounded-md border border-line px-3 py-2 text-sm font-medium text-text transition-colors hover:bg-surface-2 motion-reduce:transition-none';

/** What a reader can do next with this exact frozen version, and why not when blocked. */
export function ReportPageFooter({
  reportId,
  version,
  followUp,
}: {
  reportId: string;
  version: ReportVersion;
  followUp: ReturnType<typeof followUpAvailability>;
}) {
  const briefLink =
    version.brief_id && version.brief_revision
      ? `/research?brief=${version.brief_id}&revision=${String(version.brief_revision)}&from_report=${encodeURIComponent(reportId)}&from_report_version=${String(version.number)}`
      : null;
  return (
    <footer className="report-reader-print-hide mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-line pt-5 text-xs text-muted">
      <span>
        {version.evidence.length} retained source item
        {version.evidence.length === 1 ? '' : 's'} · Exact version {version.number}
      </span>
      {briefLink ? (
        <div className="flex flex-wrap gap-2">
          <Link to={briefLink} className={action}>
            Use this brief
          </Link>
          <Link to={`${briefLink}&intent=subscribe`} className={action}>
            Subscribe to updates
          </Link>
        </div>
      ) : (
        <span title="This version has no frozen Research Brief revision.">
          Brief reuse unavailable for this version
        </span>
      )}
      {followUp.request ? (
        <Link
          to={`/research?parent=${encodeURIComponent(reportId)}&parent_version=${String(version.number)}`}
          className={action}
        >
          Ask a follow-up question →
        </Link>
      ) : (
        <div className="flex max-w-sm flex-col items-end gap-1 text-right">
          <button
            type="button"
            disabled
            aria-describedby="follow-up-unavailable-reason"
            className="cursor-not-allowed rounded px-3 py-2 text-sm font-medium text-muted opacity-60"
          >
            Ask a follow-up question
          </button>
          <span id="follow-up-unavailable-reason" className="text-xs text-muted">
            Follow-up unavailable: {followUp.reason}
          </span>
        </div>
      )}
    </footer>
  );
}
