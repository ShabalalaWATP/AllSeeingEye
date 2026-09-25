import { useCallback, useState } from 'react';
import { Link, useParams } from 'react-router';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { fetchMonitorTransition, exportMonitorTransition } from '@/lib/api/annotationMonitors';
import { describeError } from '@/lib/api/errors';
import { annotationMonitorHref } from '@/lib/annotationMonitorLinks';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { MonitorPrivacyBoundary } from './MonitorPrivacyBoundary';
import { AnnotationComparisonResult } from './AnnotationComparisonResult';
function Contents({ id, transitionId }: { id: string; transitionId: string }) {
  const read = useScopedRequest();
  const request = useScopedRequest();
  const loader = useCallback(
    () => fetchMonitorTransition(id, transitionId, read()),
    [id, transitionId, read],
  );
  const resource = useScopedResource(loader);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const download = async () => {
    if (busy || !resource.data) return;
    const signal = request();
    setBusy(true);
    setError(null);
    try {
      const blob = await exportMonitorTransition(
        id,
        transitionId,
        resource.data.comparison.comparison_sha256,
        signal,
      );
      signal.throwIfAborted();
      saveBinaryFile(`annotation-transition-${transitionId}.json`, blob);
    } catch (caught) {
      if (!signal.aborted) setError(caught);
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  };
  return (
    <section className="space-y-5 overflow-y-auto p-6">
      <Link to={annotationMonitorHref(id)} className="text-ember underline">
        Monitor and history
      </Link>
      <h1 className="text-xl font-semibold">Stored monitoring transition</h1>
      <p className="text-sm text-muted">
        This is the exact recorded transition, including its historical comparison. Later
        corrections do not replace it.
      </p>
      {resource.loading && <LoadingNote label="Loading exact transition" />}
      {resource.error && (
        <Alert tone="error">
          {describeError(resource.error)} The exact transition is unavailable; no latest revision is
          substituted.
        </Alert>
      )}
      <Button variant="secondary" onClick={() => void resource.reload()}>
        Reload exact transition
      </Button>
      {error !== null && <Alert tone="error">{describeError(error)}</Alert>}
      {resource.data && (
        <>
          <section className="space-y-2 text-xs [overflow-wrap:anywhere]">
            <h2 className="font-semibold">
              Transition {resource.data.transition.sequence}: {resource.data.transition.kind}
            </h2>
            <p>
              Recorded {resource.data.transition.recorded_at}. This is monitoring history time, not
              the period when a source assertion was valid.
            </p>
            <p>
              Checkpoint {resource.data.transition.checkpoint_before} to{' '}
              {resource.data.transition.checkpoint_after}.
            </p>
            <p>
              Notification policy revision {resource.data.transition.configuration_revision}:{' '}
              {resource.data.transition.notification_categories.join(', ')}; notifications{' '}
              {resource.data.transition.notify_on_change ? 'on' : 'off'}.
            </p>
            <p>
              {resource.data.transition.alert_id
                ? 'An alert was recorded for this transition.'
                : 'This transition was recorded silently.'}
            </p>
          </section>
          <Button busy={busy} onClick={() => void download()}>
            Export exact transition JSON
          </Button>
          <AnnotationComparisonResult value={resource.data.comparison} />
        </>
      )}
    </section>
  );
}
export default function AnnotationTransitionPage() {
  const { monitorId, transitionId } = useParams();
  return monitorId && transitionId ? (
    <MonitorPrivacyBoundary scope={`${monitorId}:${transitionId}`}>
      <Contents id={monitorId} transitionId={transitionId} />
    </MonitorPrivacyBoundary>
  ) : (
    <Alert tone="error">Exact transition identifiers unavailable.</Alert>
  );
}
