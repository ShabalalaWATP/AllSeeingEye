/**
 * Every saved report the reader may open, whichever section created it. The section
 * pages keep their own lists; this view finds a report when its origin is forgotten.
 */
import { Link, useSearchParams } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import { Table, Td, Th } from '@/components/ui/Table';
import { describeError } from '@/lib/api/errors';
import type { DiscoveryFilter } from '@/lib/api/reportListing';
import { formatPersonalDate } from '@/lib/format';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';
import { useProfile } from '@/stores/profile';

import {
  DISCOVERY_FILTERS,
  FILTER_LABELS,
  discoveryParams,
  noMatchText,
  originLabel,
  readDiscovery,
  type DiscoveryState,
} from './reportDiscovery';
import { StatusBadge } from './StatusBadge';
import { useReportDiscovery } from './useReportDiscovery';

const CAPTION = 'Saved reports';

export default function SavedReportsPage() {
  const [params, setParams] = useSearchParams();
  const state = readDiscovery(params);
  const reports = useReportDiscovery(state);
  const workspaces = useWorkspaces();
  const preferences = useProfile();
  const go = (next: DiscoveryState) => setParams(discoveryParams(next));
  const listed = reports.data?.items ?? null;
  return (
    <section className="flex h-full flex-col gap-4 overflow-y-auto p-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Saved reports</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted">
          Research, subscription updates and geolocation assessments you can open, newest first.
          Automatic workspace briefings are not part of requested work.
        </p>
      </header>
      <div className="max-w-xs">
        <SelectField
          label="Show"
          value={state.filter}
          hint="Covers your latest 1,000 matching reports. Each section keeps its older reports."
          options={DISCOVERY_FILTERS.map((value) => ({ value, label: FILTER_LABELS[value] }))}
          onChange={(event) => go({ filter: event.target.value as DiscoveryFilter, page: 1 })}
        />
      </div>
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
        <div className="space-y-2 text-sm text-muted">
          <p>
            {state.page > 1
              ? 'No reports on this page. Return to the previous page.'
              : noMatchText(state.filter)}
          </p>
          {state.filter !== 'requested' && (
            <Button variant="secondary" onClick={() => go({ filter: 'requested', page: 1 })}>
              Show all requested work
            </Button>
          )}
        </div>
      )}
      {listed !== null && listed.length > 0 && (
        <>
          <p role="status" className="text-sm text-muted">
            Showing {listed.length} {listed.length === 1 ? 'report' : 'reports'}, page {state.page}.
          </p>
          <Table caption={CAPTION}>
            <thead>
              <tr>
                <Th>Report</Th>
                <Th>Origin</Th>
                <Th>Workspace</Th>
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
                  </Td>
                  <Td className="text-xs">{originLabel(report.origin)}</Td>
                  <Td className="text-xs text-muted">{workspaces.label(report.team_id)}</Td>
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
        </>
      )}
      <nav aria-label={`${CAPTION} pages`} className="flex items-center gap-3 text-sm">
        <Button
          variant="ghost"
          onClick={() => go({ ...state, page: state.page - 1 })}
          disabled={!reports.canPrevious || reports.loading}
        >
          Previous reports
        </Button>
        <span>Page {state.page}</span>
        <Button
          variant="ghost"
          onClick={() => go({ ...state, page: state.page + 1 })}
          disabled={!reports.canNext || reports.loading}
        >
          Next reports
        </Button>
      </nav>
    </section>
  );
}
