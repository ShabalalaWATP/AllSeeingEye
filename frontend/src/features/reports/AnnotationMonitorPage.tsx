import { useCallback, useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import {
  deleteAnnotationMonitor,
  fetchAnnotationMonitor,
  updateAnnotationMonitor,
} from '@/lib/api/annotationMonitors';
import type { MonitorUpdate } from '@/lib/api/annotationMonitors';
import { describeError, isApiError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';
import { MonitorPrivacyBoundary } from './MonitorPrivacyBoundary';
import { MonitorConfiguration } from './MonitorConfiguration';
import { MonitorResumeControls } from './MonitorResumeControls';
import { MonitorRemoval } from './MonitorRemoval';
import { MonitorTransitionHistory } from './MonitorTransitionHistory';
function Contents({ id }: { id: string }) {
  const navigate = useNavigate();
  const read = useScopedRequest();
  const request = useScopedRequest();
  const loader = useCallback(() => fetchAnnotationMonitor(id, read()), [id, read]);
  const resource = useScopedResource(loader);
  const workspaces = useWorkspaces();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const update = async (body: MonitorUpdate) => {
    if (busy) return;
    const signal = request();
    setBusy(true);
    setError(null);
    try {
      const value = await updateAnnotationMonitor(id, body, signal);
      signal.throwIfAborted();
      resource.setData(value);
    } catch (caught) {
      if (!signal.aborted) setError(caught);
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  };
  const remove = async () => {
    if (busy || !resource.data) return;
    const signal = request();
    setBusy(true);
    setError(null);
    try {
      await deleteAnnotationMonitor(id, resource.data.revision, signal);
      signal.throwIfAborted();
      void navigate('/annotation-monitors');
    } catch (caught) {
      if (!signal.aborted) setError(caught);
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  };
  const monitor = resource.data;
  const conflict = isApiError(error) && error.status === 409;
  return (
    <main className="space-y-5 overflow-y-auto p-6">
      <Link to="/annotation-monitors" className="text-ember underline">
        All annotation monitors
      </Link>
      <h1 className="text-xl font-semibold">{monitor?.name ?? 'Annotation monitor'}</h1>
      {resource.loading && <LoadingNote label="Loading monitor" />}
      {resource.error && <Alert tone="error">{describeError(resource.error)}</Alert>}
      <Button
        variant="secondary"
        disabled={busy}
        onClick={() => {
          setError(null);
          void resource.reload();
        }}
      >
        Reload monitor state
      </Button>
      {error !== null && (
        <Alert tone="error">
          {describeError(error)}
          {conflict &&
            ' The checkpoint or configuration changed. Reload monitor state before editing again.'}
        </Alert>
      )}
      {monitor && (
        <>
          <p className="text-sm">
            Status: {monitor.status}. Checkpoint {monitor.checkpoint_number}. Updated{' '}
            {monitor.updated_at}.
          </p>
          <p className="text-xs text-muted">
            Updated is the state/configuration timestamp, not proof of a successful observation.
            Recorded transitions retain their own observation times.
          </p>
          <Link
            className="text-ember underline"
            to={`/reports/${encodeURIComponent(monitor.report_id)}?version=${monitor.version_number}`}
          >
            Pinned report version {monitor.version_number}
          </Link>
          {workspaces.canManage(monitor) && (
            <MonitorRemoval busy={busy || conflict} onRemove={() => void remove()} />
          )}
          <details>
            <summary>Exact watched roots and checkpoint revisions</summary>
            <p className="text-xs text-muted">
              New roots are not enrolled automatically. Checkpoint ID {monitor.checkpoint_id}.
            </p>
            <ul className="space-y-1 text-xs [overflow-wrap:anywhere]">
              {monitor.selection.revisions.map((item) => (
                <li key={item.claim_id}>
                  Claim {item.claim_id}: {item.revision_id}
                </li>
              ))}
              {monitor.selection.identity_revisions.map((item) => (
                <li key={item.decision_id}>
                  Identity review {item.decision_id}: {item.revision_id}
                </li>
              ))}
              {monitor.selection.relationship_revisions.map((item) => (
                <li key={item.relationship_id}>
                  Relationship review {item.relationship_id}: {item.revision_id}
                </li>
              ))}
            </ul>
          </details>
          {monitor.status === 'unavailable' ? (
            <Alert tone="warning">
              Unavailable:{' '}
              {monitor.unavailable_reason ?? 'The stored inputs cannot currently be accessed.'} No
              unchanged result is inferred.
            </Alert>
          ) : (
            <>
              {workspaces.canManage(monitor) && (
                <div key={`configuration:${monitor.revision}`} className="space-y-4">
                  <MonitorConfiguration
                    monitor={monitor}
                    busy={busy || conflict}
                    onSave={(body) => void update(body)}
                  />
                  {monitor.status === 'active' ? (
                    <Button
                      variant="secondary"
                      disabled={busy || conflict}
                      onClick={() =>
                        void update({
                          expected_revision: monitor.revision,
                          action: 'pause',
                          rebaseline: false,
                        })
                      }
                    >
                      Pause monitoring
                    </Button>
                  ) : (
                    <MonitorResumeControls
                      busy={busy || conflict}
                      onCatchUp={() =>
                        void update({
                          expected_revision: monitor.revision,
                          action: 'resume_catch_up',
                          rebaseline: false,
                        })
                      }
                      onFreshBaseline={() =>
                        void update({
                          expected_revision: monitor.revision,
                          action: 'resume_rebaseline',
                          rebaseline: false,
                        })
                      }
                    />
                  )}
                </div>
              )}
              <MonitorTransitionHistory key={`history:${monitor.revision}`} id={id} />
            </>
          )}
        </>
      )}
    </main>
  );
}
export default function AnnotationMonitorPage() {
  const { monitorId } = useParams();
  return monitorId ? (
    <MonitorPrivacyBoundary scope={monitorId}>
      <Contents id={monitorId} />
    </MonitorPrivacyBoundary>
  ) : (
    <Alert tone="error">Monitor identifier unavailable.</Alert>
  );
}
