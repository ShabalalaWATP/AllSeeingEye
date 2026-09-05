import { useCallback } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { CopyButton } from '@/components/ui/CopyButton';
import { describeError } from '@/lib/api/errors';
import {
  deleteReport,
  fetchReport,
  fetchReportMarkdown,
  regenerateReport,
} from '@/lib/api/reports';
import { fileNameFor, saveTextFile } from '@/lib/download';
import { formatUtc } from '@/lib/format';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useResource } from '@/lib/hooks/useResource';

import { EvidenceAnnex, ReportBodyView } from './ReportSections';
import { StatusBadge } from './ReportsPage';

function versionFromQuery(value: string | null): number | undefined {
  const parsed = Number(value);
  return value !== null && Number.isInteger(parsed) && parsed >= 1 ? parsed : undefined;
}

export default function ReportPage() {
  const { id = '' } = useParams();
  const [params] = useSearchParams();
  const requested = versionFromQuery(params.get('version'));
  const navigate = useNavigate();
  const loader = useCallback(() => fetchReport(id, requested), [id, requested]);
  const { data, error, loading, reload } = useResource(loader);
  const remove = useAsyncAction(async () => {
    await deleteReport(id);
    await navigate('/reports');
  });
  const regenerate = useAsyncAction(async () => {
    await regenerateReport(id);
    await navigate(`/reports/${id}`);
    await reload();
  });
  const download = useAsyncAction(async () => {
    if (data === null) return;
    const text = await fetchReportMarkdown(id, data.version.number);
    saveTextFile(fileNameFor(`${data.report.title}-v${data.version.number}`, 'md'), text);
  });

  if (data === null) {
    return (
      <section className="p-6">
        {error === null ? null : <Alert tone="error">{describeError(error)}</Alert>}
        {loading ? <LoadingNote label="Loading report" /> : null}
      </section>
    );
  }
  const { report, version } = data;
  const versions = Array.from({ length: report.latest_version }, (_, index) => index + 1);
  const actionError = remove.error ?? regenerate.error ?? download.error;
  return (
    <article className="flex h-full flex-col gap-6 overflow-y-auto p-6">
      <header className="flex flex-col gap-2">
        <Link to="/reports" className="text-xs text-muted hover:underline">
          All reports
        </Link>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-semibold">{report.title}</h1>
          <StatusBadge status={version.status} />
        </div>
        <p className="font-mono text-xs text-muted">
          {report.template} · period {formatUtc(report.period_from)} to{' '}
          {formatUtc(report.period_to)} · {version.model} · {version.attempts} attempt
          {version.attempts === 1 ? '' : 's'} · {version.prompt_tokens ?? 0} +{' '}
          {version.completion_tokens ?? 0} tokens · {Math.round(version.latency_ms)} ms
        </p>
        <nav aria-label="Versions" className="flex flex-wrap items-center gap-1 text-xs">
          <span className="text-muted">Version</span>
          {versions.map((number) => (
            <Link
              key={number}
              to={`/reports/${id}?version=${String(number)}`}
              aria-current={number === version.number ? 'page' : undefined}
              className={`rounded px-1.5 py-0.5 font-mono ${
                number === version.number ? 'bg-surface-2 text-text' : 'text-muted hover:text-text'
              }`}
            >
              {number}
            </Link>
          ))}
        </nav>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" busy={regenerate.busy} onClick={() => void regenerate.run()}>
            Regenerate
          </Button>
          <Button variant="secondary" busy={download.busy} onClick={() => void download.run()}>
            Download Markdown
          </Button>
          <CopyButton value={version.markdown} label="Copy Markdown" />
          <Button variant="danger" busy={remove.busy} onClick={() => void remove.run()}>
            Delete
          </Button>
        </div>
        {actionError === null ? null : <Alert tone="error">{describeError(actionError)}</Alert>}
      </header>
      {version.status !== 'ready' && (
        <Alert tone={version.status === 'failed' ? 'error' : 'warning'} title="Validator findings">
          <ul className="list-disc pl-5">
            {version.findings.map((finding, index) => (
              <li key={index}>
                <span className="font-mono text-xs">{finding.severity}</span> {finding.location}:{' '}
                {finding.message}
              </li>
            ))}
          </ul>
        </Alert>
      )}
      <ReportBodyView body={version.body} />
      <EvidenceAnnex
        evidence={version.evidence}
        findings={version.findings}
        status={version.status}
      />
    </article>
  );
}
