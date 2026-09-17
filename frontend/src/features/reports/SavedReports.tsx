/**
 * The saved reports of one section: research questions, subscription updates or
 * geolocation assessments. Each section lists its own, so a reader looks for a past
 * answer where they asked the question rather than in a separate library.
 */
import { Link } from 'react-router';

import { LibraryButton } from '@/components/library/LibraryButton';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Table, Td, Th } from '@/components/ui/Table';
import { describeError } from '@/lib/api/errors';
import { fetchReports } from '@/lib/api/reports';
import { formatPersonalDate, formatUtc } from '@/lib/format';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';
import { useProfile } from '@/stores/profile';

import { StatusBadge } from './StatusBadge';
import { reportsFrom, type SavedOrigin } from './savedReportOrigin';

export function SavedReports({
  origin,
  caption,
  empty,
  onChanged,
}: {
  origin: SavedOrigin;
  caption: string;
  empty: string;
  onChanged?: () => void;
}) {
  const preferences = useProfile();
  const workspaces = useWorkspaces();
  const reports = useScopedResource(fetchReports);
  const listed = reportsFrom(reports.data, origin);
  const changed = onChanged ?? reports.reload;
  if (reports.error !== null) return <Alert tone="error">{describeError(reports.error)}</Alert>;
  if (listed === null) return reports.loading ? <LoadingNote label="Loading reports" /> : null;
  if (listed.length === 0) return <p className="text-sm text-muted">{empty}</p>;
  return (
    <div className="shrink-0">
      <Table caption={caption}>
        <thead>
          <tr>
            <Th>Report</Th>
            <Th>Period</Th>
            <Th>Status</Th>
            <Th>Created</Th>
          </tr>
        </thead>
        <tbody>
          {listed.map((report) => (
            <tr key={report.id}>
              <Td>
                <Link
                  to={`/reports/${report.id}`}
                  className="font-medium text-text hover:underline"
                >
                  {report.title}
                </Link>
                <div className="font-mono text-xs text-muted">
                  {report.template} · {workspaces.label(report.team_id)}
                </div>
                <LibraryButton reportId={report.id} onChanged={changed} />
              </Td>
              <Td className="whitespace-nowrap text-xs text-muted">
                {formatUtc(report.period_from)} to {formatUtc(report.period_to)}
              </Td>
              <Td>
                <StatusBadge status={report.status} />
              </Td>
              <Td className="whitespace-nowrap text-xs text-muted">
                {formatPersonalDate(report.created_at, preferences.profile)}
              </Td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
}
