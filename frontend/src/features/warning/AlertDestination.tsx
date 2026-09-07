import { Link } from 'react-router';
import { annotationTransitionHref } from '@/lib/annotationMonitorLinks';
export function AlertDestination({
  monitorId,
  transitionId,
  reportId,
}: {
  monitorId: string | null;
  transitionId: string | null;
  reportId: string | null;
}) {
  if (monitorId !== null)
    return transitionId !== null ? (
      <Link
        to={annotationTransitionHref(monitorId, transitionId)}
        className="text-text hover:underline"
      >
        Exact annotation transition
      </Link>
    ) : (
      <span className="text-muted">Exact annotation transition unavailable</span>
    );
  return reportId !== null ? (
    <Link to={`/reports/${encodeURIComponent(reportId)}`} className="text-text hover:underline">
      Report
    </Link>
  ) : null;
}
