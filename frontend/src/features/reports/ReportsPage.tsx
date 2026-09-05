import { useCallback, useEffect } from 'react';
import { Link, useNavigate } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Table, Td, Th } from '@/components/ui/Table';
import { describeError } from '@/lib/api/errors';
import { fetchReports, fetchTemplates, generateReport } from '@/lib/api/reports';
import type { ReportRequest } from '@/lib/api/reports';
import { STATUS_LABELS } from '@/lib/doctrine';
import { formatUtc } from '@/lib/format';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useResource } from '@/lib/hooks/useResource';
import { useCountriesStore } from '@/stores/countries';

import { GenerateForm } from './GenerateForm';

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
  const navigate = useNavigate();
  const reports = useResource(fetchReports);
  const templates = useResource(fetchTemplates);
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
      {templates.data === null ? (
        templates.loading ? (
          <LoadingNote label="Loading products" />
        ) : null
      ) : (
        <GenerateForm
          templates={templates.data}
          countries={countries}
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
                  <div className="font-mono text-xs text-muted">{report.template}</div>
                </Td>
                <Td className="whitespace-nowrap text-xs text-muted">
                  {formatUtc(report.period_from)} to {formatUtc(report.period_to)}
                </Td>
                <Td>
                  <StatusBadge status={report.status} />
                </Td>
                <Td className="whitespace-nowrap text-xs text-muted">
                  {formatUtc(report.created_at)}
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </section>
  );
}
