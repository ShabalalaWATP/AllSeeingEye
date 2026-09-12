import { Button } from '@/components/ui/Button';
import { useProfile } from '@/stores/profile';
import { useState } from 'react';
import { ResearchLibrary } from '@/components/library/ResearchLibrary';
import { LibraryButton } from '@/components/library/LibraryButton';
import { Link, useSearchParams } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Table, Td, Th } from '@/components/ui/Table';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';

import { describeError } from '@/lib/api/errors';
import { fetchReports } from '@/lib/api/reports';
import { STATUS_LABELS } from '@/lib/doctrine';
import { formatPersonalDate, formatUtc } from '@/lib/format';

import { TemplateReportComposer } from './TemplateReportComposer';
import { ReportSearch } from './ReportSearch';

const STATUS_CLASSES: Record<string, string> = {
  ready: 'bg-emerald-400/15 text-emerald-300',
  needs_review: 'bg-amber-400/15 text-amber-300',
  failed: 'bg-critical/15 text-critical',
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`rounded px-1.5 py-0.5 font-mono text-[11px] uppercase ${
        STATUS_CLASSES[status] ?? 'bg-zinc-500/15 text-muted'
      }`}
    >
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

export default function ReportsPage() {
  const [libraryRevision, setLibraryRevision] = useState(0);
  const libraryChanged = () => setLibraryRevision((revision) => revision + 1);
  const preferences = useProfile();
  const [params] = useSearchParams();
  const reports = useScopedResource(fetchReports);
  const workspaces = useWorkspaces();
  const [showComposer, setShowComposer] = useState(false);
  const [closedContext, setClosedContext] = useState<string | null>(null);
  const initial = Object.fromEntries(
    ['template', 'country', 'conflict', 'hazard', 'plan']
      .map((key) => [key, params.get(key)])
      .filter((entry): entry is [string, string] => entry[1] !== null),
  );
  const composerVisible =
    showComposer || (Object.keys(initial).length > 0 && closedContext !== params.toString());

  return (
    <section className="flex h-full flex-col gap-4 overflow-y-auto p-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Saved reports</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted">
            Find previous answers, inspect frozen evidence and export your findings. Subscription
            updates and daily briefings are saved here too.
          </p>
        </div>
        <Link
          to="/research"
          className="rounded-md bg-ember px-4 py-3 text-sm font-medium text-ground"
        >
          New research
        </Link>
      </header>
      <div className="flex flex-wrap gap-4 text-sm">
        <Link to="/research/jobs" className="text-muted underline hover:text-text">
          Research progress
        </Link>
        <Link to="/subscriptions" className="text-muted underline hover:text-text">
          Manage subscriptions
        </Link>
        <Button
          variant="ghost"
          aria-expanded={composerVisible}
          onClick={() => {
            setShowComposer(!composerVisible);
            if (composerVisible) setClosedContext(params.toString());
          }}
        >
          Specialist report templates
        </Button>
      </div>
      <ReportSearch />
      <ResearchLibrary revision={libraryRevision} onChanged={libraryChanged} />
      {!preferences.profile && preferences.error && (
        <Alert tone="error">
          Report preferences could not be loaded.{' '}
          <Button variant="secondary" onClick={() => void preferences.reload()}>
            Retry preferences
          </Button>
        </Alert>
      )}
      {composerVisible && <TemplateReportComposer initial={initial} />}
      {reports.error === null ? null : <Alert tone="error">{describeError(reports.error)}</Alert>}
      {reports.data === null ? (
        reports.loading ? (
          <LoadingNote label="Loading reports" />
        ) : null
      ) : reports.data.length === 0 ? (
        <p className="text-sm text-muted">
          No saved reports yet. Start a research question to create your first report.
        </p>
      ) : (
        <div className="shrink-0">
          <Table caption="Reports">
            <thead>
              <tr>
                <Th>Report</Th>
                <Th>Period</Th>
                <Th>Status</Th>
                <Th>Created</Th>
              </tr>
            </thead>
            <tbody>
              {reports.data.map((report) => (
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
                    <LibraryButton reportId={report.id} onChanged={libraryChanged} />
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
      )}
    </section>
  );
}
