import { StatusPill } from '@/components/admin/StatusPill';
import { Button } from '@/components/ui/Button';
import { Table, Td, Th } from '@/components/ui/Table';
import type { EvaluationCaseResult, EvaluationRun } from '@/lib/api/evaluations';
import { formatUtc } from '@/lib/format';

import {
  CHECK_LABELS,
  describeRun,
  formatCheck,
  formatTokens,
  isRatioCheck,
} from './evaluationPresentation';

const SHOWN_CHECKS = [
  'final_citation_reference_validity',
  'required_evidence_cited_recall',
  'counterevidence_referenced_any_role_recall',
  'uncited_statement_fields',
  'validation_errors',
] as const;

function CaseRow({ result }: { result: EvaluationCaseResult }) {
  return (
    <tr>
      <Td className="py-2 font-mono text-xs">{result.case_id}</Td>
      <Td className="py-2 text-sm">{result.report_status}</Td>
      <Td className="py-2 text-sm">{result.model_calls}</Td>
      {SHOWN_CHECKS.map((name) => (
        <Td key={name} className="py-2 text-sm">
          {formatCheck(result.checks[name], isRatioCheck(name))}
        </Td>
      ))}
    </tr>
  );
}

/** One run: progress against the cap, structural checks per case, cancel and download. */
export function EvaluationRunCard({
  run,
  busy,
  onCancel,
  onDownload,
}: {
  run: EvaluationRun;
  busy: boolean;
  onCancel: (runId: string) => void;
  onDownload: (run: EvaluationRun) => void;
}) {
  const status = describeRun(run);
  return (
    <article
      aria-label={`Evaluation of ${run.profile_name}, started ${formatUtc(run.created_at)}`}
      className="grid gap-3 border border-line bg-surface/50 p-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-semibold">
            {run.profile_name} <span className="font-mono text-xs text-muted">{run.model}</span>
          </p>
          <p className="text-xs text-muted">Started {formatUtc(run.created_at)}</p>
        </div>
        <StatusPill tone={status.tone}>{status.label}</StatusPill>
      </div>
      <dl className="grid gap-2 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-muted">Cases finished</dt>
          <dd>
            {run.results.length} of {run.case_ids.length}
          </dd>
        </div>
        <div>
          <dt className="text-muted">Calls reserved</dt>
          <dd>
            {run.calls_reserved} of {run.max_calls} (estimate {run.estimated_calls})
          </dd>
        </div>
        <div>
          <dt className="text-muted">Failed calls</dt>
          <dd>{run.calls_failed}</dd>
        </div>
        <div>
          <dt className="text-muted">Tokens (prompt / completion)</dt>
          <dd>
            {formatTokens(run.prompt_tokens)} / {formatTokens(run.completion_tokens)}
          </dd>
        </div>
      </dl>
      {run.results.length === 0 ? null : (
        <p className="text-xs font-semibold">Structural checks per case (not accuracy)</p>
      )}
      {run.results.length === 0 ? null : (
        <Table caption="Structural checks per case, not accuracy">
          <thead>
            <tr>
              <Th>Case</Th>
              <Th>Report status</Th>
              <Th>Calls</Th>
              {SHOWN_CHECKS.map((name) => (
                <Th key={name}>{CHECK_LABELS[name]}</Th>
              ))}
            </tr>
          </thead>
          <tbody>
            {run.results.map((result) => (
              <CaseRow key={result.case_id} result={result} />
            ))}
          </tbody>
        </Table>
      )}
      <p className="text-xs text-muted">{run.notice}</p>
      <div className="flex flex-wrap gap-2">
        {run.status === 'running' ? (
          <Button
            variant="danger"
            disabled={run.cancel_requested}
            busy={busy}
            onClick={() => onCancel(run.id)}
          >
            Cancel run
          </Button>
        ) : null}
        {run.has_artefact ? (
          <Button variant="secondary" busy={busy} onClick={() => onDownload(run)}>
            Download results
          </Button>
        ) : null}
      </div>
    </article>
  );
}
