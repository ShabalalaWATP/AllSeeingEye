import { Link } from 'react-router';
import type { AssistantReportSelection } from '@/lib/assistantReportContext';
import { formatUtc } from '@/lib/format';
import { researchHref } from '@/lib/researchNavigation';
import { researchDateError } from '@/lib/researchPeriod';

export function EyeReportContext({
  report,
  onMapChat,
}: {
  report: AssistantReportSelection;
  onMapChat: () => void;
}) {
  return (
    <div className="eye-report-context" aria-label="Selected report edition">
      <span className="eye-report-context-label">FROZEN REPORT · VERSION {report.version}</span>
      <strong title={report.title}>{report.title}</strong>
      <span>
        {report.dataCutoff ? (
          <>
            Data cutoff <time dateTime={report.dataCutoff}>{formatUtc(report.dataCutoff)}</time>
          </>
        ) : (
          'Data cutoff unavailable in this edition'
        )}
      </span>
      <p>Questions use only this saved edition and its retained evidence.</p>
      <button type="button" onClick={onMapChat}>
        Start a map sources chat
      </button>
    </div>
  );
}

export function EyeNewerResearchLink({
  question,
  report,
  onNavigate,
}: {
  question: string;
  report: AssistantReportSelection;
  onNavigate: () => void;
}) {
  const period = report.dataCutoff
    ? { since: report.dataCutoff, until: new Date().toISOString() }
    : null;
  const initialDates = period && !researchDateError(period) ? period : null;
  return (
    <div className="eye-research-link">
      <Link to={researchHref(question, null, initialDates)} onClick={onNavigate}>
        Search for newer evidence in Research →
      </Link>
      <span>
        Opens a separate reviewable draft.{' '}
        {initialDates
          ? 'Dates start at this edition’s data cutoff. '
          : 'Choose an observation period. '}
        Review scope and sources before running. This report and its answers stay frozen.
      </span>
    </div>
  );
}
