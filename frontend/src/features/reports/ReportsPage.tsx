import { Button } from '@/components/ui/Button';
import { useProfile } from '@/stores/profile';
import { useCallback, useEffect, useState } from 'react';
import { ResearchLibrary } from '@/components/library/ResearchLibrary';
import { LibraryButton } from '@/components/library/LibraryButton';
import { Link, useNavigate, useSearchParams } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Table, Td, Th } from '@/components/ui/Table';
import { fetchPlans } from '@/lib/api/direction';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';

import { describeError } from '@/lib/api/errors';
import { fetchReports, fetchTemplates, generateReport } from '@/lib/api/reports';
import { fetchConflictBoard, fetchDisasterBoard } from '@/lib/api/trackers';
import type { ReportRequest } from '@/lib/api/reports';
import { STATUS_LABELS } from '@/lib/doctrine';
import { formatPersonalDate, formatUtc } from '@/lib/format';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useResource } from '@/lib/hooks/useResource';
import { useCountriesStore } from '@/stores/countries';

import { GenerateForm } from './GenerateForm';
import { SchedulesSection } from './SchedulesSection';
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
  const navigate = useNavigate();
  const preferences = useProfile();
  const [params] = useSearchParams();
  const reports = useScopedResource(fetchReports);
  const plans = useScopedResource(fetchPlans);
  const workspaces = useWorkspaces();
  const templates = useResource(fetchTemplates);
  const conflicts = useResource(fetchConflictBoard);
  const hazards = useResource(fetchDisasterBoard);
  const initial = Object.fromEntries(
    ['template', 'country', 'conflict', 'hazard', 'plan']
      .map((key) => [key, params.get(key)])
      .filter((entry): entry is [string, string] => entry[1] !== null),
  );
  const countries = useCountriesStore((state) => state.items);
  const loadCountries = useCountriesStore((state) => state.load);
  useEffect(() => {
    void loadCountries();
  }, [loadCountries]);

  const generate = useAsyncAction(
    useCallback(
      async (request: ReportRequest) => {
        const created = await generateReport(request);
        await navigate(`/reports/${created.report.id}`);
      },
      [navigate],
    ),
  );

  return (
    <section className="flex h-full flex-col gap-4 overflow-y-auto p-6">
      <h1 className="text-xl font-semibold">Reports</h1>
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
      {templates.data === null || !preferences.profile ? (
        templates.loading || (!preferences.profile && !preferences.error) ? (
          <LoadingNote label="Loading products" />
        ) : null
      ) : (
        <GenerateForm
          key={`${workspaces.key}:${params.toString()}`}
          preferences={preferences.profile}
          workspaces={workspaces}
          plans={plans.data ?? []}
          templates={templates.data}
          countries={countries}
          conflicts={(conflicts.data ?? []).map((card) => ({
            id: card.conflict.id,
            label: card.conflict.name,
          }))}
          hazards={(hazards.data ?? []).map((card) => ({ id: card.hazard, label: card.title }))}
          initial={initial}
          busy={generate.busy}
          error={generate.error === null ? null : describeError(generate.error)}
          onSubmit={(request) => void generate.run(request)}
        />
      )}
      {templates.error === null ? null : (
        <Alert tone="error">{describeError(templates.error)}</Alert>
      )}
      {reports.error === null ? null : <Alert tone="error">{describeError(reports.error)}</Alert>}
      {reports.data === null ? (
        reports.loading ? (
          <LoadingNote label="Loading reports" />
        ) : null
      ) : reports.data.length === 0 ? (
        <p className="text-sm text-muted">No reports yet. Generate one from the live evidence.</p>
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
      <SchedulesSection
        workspaces={workspaces}
        plans={plans.data ?? []}
        templates={templates.data ?? []}
        countries={countries}
      />
    </section>
  );
}
