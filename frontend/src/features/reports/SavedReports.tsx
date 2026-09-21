/**
 * The saved reports of one section: research questions, subscription updates or
 * geolocation assessments. Each section lists its own, so a reader looks for a past
 * answer where they asked the question rather than in a separate library.
 */
import { Link } from 'react-router';

import { LibraryButton } from '@/components/library/LibraryButton';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Table, Td, Th } from '@/components/ui/Table';
import { describeError } from '@/lib/api/errors';
import { formatPersonalDate, formatUtc } from '@/lib/format';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';
import { useProfile } from '@/stores/profile';

import { StatusBadge } from './StatusBadge';
import type { SavedOrigin } from './savedReportOrigin';
import { useSavedReports } from './useSavedReports';

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
  const reports = useSavedReports(origin);
  const listed = reports.data?.items ?? null;
  const changed = onChanged ?? reports.reload;
  return (
    <div className="shrink-0 space-y-3">
      {reports.error && (
        <Alert tone="error">
          {describeError(reports.error)}
          <Button variant="ghost" onClick={() => void reports.reload()}>
            Retry reports
          </Button>
        </Alert>
      )}
      {reports.loading && <LoadingNote label="Loading reports" />}
      {listed?.length === 0 && (
        <p className="text-sm text-muted">
          {reports.canPrevious ? 'No reports on this page. Return to the previous page.' : empty}
        </p>
      )}
      {listed !== null && listed.length > 0 && (
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
      )}
      <nav aria-label={`${caption} pages`} className="flex items-center gap-3 text-sm">
        <Button
          variant="ghost"
          onClick={reports.previous}
          disabled={!reports.canPrevious || reports.loading}
        >
          Previous reports
        </Button>
        <span aria-live="polite">Page {reports.pageNumber}</span>
        <Button
          variant="ghost"
          onClick={reports.next}
          disabled={!reports.canNext || reports.loading}
        >
          Next reports
        </Button>
      </nav>
    </div>
  );
}
