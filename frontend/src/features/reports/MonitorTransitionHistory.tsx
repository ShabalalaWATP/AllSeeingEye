import { useCallback, useState } from 'react';
import { Link } from 'react-router';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { listMonitorTransitions } from '@/lib/api/annotationMonitors';
import { describeError } from '@/lib/api/errors';
import { annotationTransitionHref } from '@/lib/annotationMonitorLinks';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { MonitorPagination } from './MonitorPagination';
export function MonitorTransitionHistory({ id }: { id: string }) {
  const [offset, setOffset] = useState(0);
  const request = useScopedRequest();
  const loader = useCallback(
    () => listMonitorTransitions(id, offset, request()),
    [id, offset, request],
  );
  const resource = useScopedResource(loader);
  return (
    <section aria-label="Recorded transitions" className="space-y-3 border-t border-line pt-4">
      <h2 className="font-semibold">Recorded transitions</h2>
      <p className="text-xs text-muted">
        Each entry opens its stored comparison and checkpoint history. Silent administrative or
        provenance changes are retained. An empty history is not proof that an observation
        succeeded.
      </p>
      <Button variant="secondary" onClick={() => void resource.reload()}>
        Refresh transition history
      </Button>
      {resource.loading && <LoadingNote label="Loading recorded transitions" />}
      {resource.error && (
        <Alert tone="error">
          {describeError(resource.error)} No latest comparison is substituted.
        </Alert>
      )}
      {resource.data && (
        <>
          {resource.data.items.length === 0 ? (
            <p className="text-sm text-muted">
              No transitions recorded after the initial silent baseline.
            </p>
          ) : (
            <ol className="divide-y divide-line">
              {resource.data.items.map((item) => (
                <li key={item.id} className="space-y-1 py-3">
                  <Link className="text-ember underline" to={annotationTransitionHref(id, item.id)}>
                    Transition {item.sequence}:{' '}
                    {item.kind === 'rebaseline' ? 'Fresh baseline' : 'Annotation revision'}
                  </Link>
                  <p className="text-xs text-muted">
                    Recorded {item.recorded_at};{' '}
                    {item.changed_categories.length
                      ? item.changed_categories.join(', ')
                      : 'no selected substantive category change'}
                    ; {item.alert_id ? 'alert recorded' : 'silent transition'}.
                  </p>
                </li>
              ))}
            </ol>
          )}
          <MonitorPagination
            label="transition"
            offset={offset}
            total={resource.data.total}
            count={resource.data.items.length}
            onChange={setOffset}
          />
        </>
      )}
    </section>
  );
}
