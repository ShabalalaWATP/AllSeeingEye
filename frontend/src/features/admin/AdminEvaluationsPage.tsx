import { AdminPage, AdminSection, EmptyState } from '@/components/admin/AdminPage';
import { StatusPill } from '@/components/admin/StatusPill';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { describeError } from '@/lib/api/errors';

import { EvaluationRunCard } from './evaluations/EvaluationRunCard';
import { EvaluationStartForm } from './evaluations/EvaluationStartForm';
import { useEvaluations } from './evaluations/useEvaluations';

export default function AdminEvaluationsPage() {
  const { catalogue, profiles, runs, loading, busy, error, start, cancel, download } =
    useEvaluations();
  const running = runs.some((run) => run.status === 'running');

  return (
    <AdminPage
      eyebrow="Research services"
      title="Evaluations"
      description="Run selected synthetic cases against a saved AI connection to check a new model or prompt. Every call is metered through the AI allowance ledger and stops at the call cap. Results are structural checks for human review, not accuracy."
      meta={
        running ? (
          <StatusPill tone="info" icon="clock">
            A run is in progress
          </StatusPill>
        ) : undefined
      }
    >
      {error === null ? null : <Alert tone="error">{describeError(error)}</Alert>}
      {catalogue === null ? (
        loading ? (
          <LoadingNote label="Loading the evaluation casebook" />
        ) : null
      ) : (
        <>
          <Alert tone="info" title="What these results mean">
            {catalogue.result_notice} Human semantic review stays a separate step using the
            downloaded review template.
          </Alert>
          <AdminSection title="Start a run" icon="evaluations">
            <EvaluationStartForm
              catalogue={catalogue}
              profiles={profiles}
              busy={busy}
              running={running}
              onStart={start}
            />
          </AdminSection>
          <AdminSection title="Recent runs" icon="audit">
            {runs.length === 0 ? (
              <EmptyState icon="evaluations" title="No evaluation runs yet.">
                Started runs, their call usage and structural checks appear here.
              </EmptyState>
            ) : (
              <div className="grid gap-3">
                {runs.map((run) => (
                  <EvaluationRunCard
                    key={run.id}
                    run={run}
                    busy={busy}
                    onCancel={(id) => void cancel(id)}
                    onDownload={(item) => void download(item)}
                  />
                ))}
              </div>
            )}
          </AdminSection>
        </>
      )}
    </AdminPage>
  );
}
