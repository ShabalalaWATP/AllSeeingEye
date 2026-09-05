import { useCallback } from 'react';
import { Link, useNavigate, useParams } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { CopyButton } from '@/components/ui/CopyButton';
import { describeError } from '@/lib/api/errors';
import { deleteReport, fetchReport } from '@/lib/api/reports';
import { formatUtc } from '@/lib/format';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useResource } from '@/lib/hooks/useResource';

import { EvidenceAnnex } from './ReportSections';
import { ReportBodyView } from './ReportSections';
import { StatusBadge } from './ReportsPage';

export default function ReportPage() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const loader = useCallback(() => fetchReport(id), [id]);
  const { data, error, loading } = useResource(loader);
  const remove = useAsyncAction(async () => {
    await deleteReport(id);
    await navigate('/reports');
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
          {formatUtc(report.period_to)} · version {version.number} · {version.model} ·{' '}
          {version.attempts} attempt{version.attempts === 1 ? '' : 's'} ·{' '}
          {version.prompt_tokens ?? 0} + {version.completion_tokens ?? 0} tokens ·{' '}
          {Math.round(version.latency_ms)} ms
        </p>
        <div className="flex flex-wrap gap-2">
          <CopyButton value={version.markdown} label="Copy Markdown" />
          <Button variant="danger" busy={remove.busy} onClick={() => void remove.run()}>
            Delete
          </Button>
        </div>
        {remove.error === null ? null : <Alert tone="error">{describeError(remove.error)}</Alert>}
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
