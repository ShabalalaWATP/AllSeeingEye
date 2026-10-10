import { Link } from 'react-router';

import type { Alert } from '@/lib/api/warning';

const LABELS = {
  pending: 'Report waiting to be queued.',
  queued: 'Report queued.',
  running: 'Report in progress.',
  paused: 'Report paused. Open its progress to review the reason and available actions.',
  failed: 'Report could not be completed.',
  completed: 'Report completed.',
  needs_review: 'Report completed and needs review.',
  cancelled: 'Report cancelled because its alert rule or workspace access changed.',
  discarded: 'Report progress was discarded.',
} as const;

export function AlertReportProgress({ alert }: { alert: Alert }) {
  if (!alert.report_status) return null;
  const label =
    alert.report_error === 'capacity_wait'
      ? 'Report waiting for capacity. Admission will be checked again.'
      : alert.report_error === 'admission_failed'
        ? 'Report could not be queued. Check the rule and model configuration before the next alert.'
        : alert.report_error === 'admission_expired'
          ? 'Report was not queued within 24 hours.'
          : LABELS[alert.report_status];
  return (
    <p className="text-xs text-muted">
      {label}{' '}
      {alert.report_job_id && (
        <Link className="text-accent underline" to={`/research/jobs/${alert.report_job_id}`}>
          View report progress
        </Link>
      )}
    </p>
  );
}
