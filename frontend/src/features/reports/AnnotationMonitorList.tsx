import { useCallback, useState } from 'react';
import { Link } from 'react-router';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { listAnnotationMonitors } from '@/lib/api/annotationMonitors';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { annotationMonitorHref } from '@/lib/annotationMonitorLinks';
import { MonitorPagination } from './MonitorPagination';
export function AnnotationMonitorList({
  scope,
}: {
  scope?: { reportId: string; version: number };
}) {
  const [offset, setOffset] = useState(0);
  const request = useScopedRequest();
  const reportId = scope?.reportId;
  const version = scope?.version;
  const loader = useCallback(
    () =>
      listAnnotationMonitors(
        offset,
        request(),
        reportId !== undefined && version !== undefined ? { reportId, version } : undefined,
      ),
    [offset, request, reportId, version],
  );
  const resource = useScopedResource(loader);
  return (
    <section aria-label="Annotation monitors" className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">Annotation monitors</h2>
        <Button variant="secondary" onClick={() => void resource.reload()}>
          Refresh monitors
        </Button>
      </div>
      {resource.loading && <LoadingNote label="Loading annotation monitors" />}
      {resource.error && <Alert tone="error">{describeError(resource.error)}</Alert>}
      {resource.data && (
        <>
          {resource.data.items.length === 0 ? (
            <p className="text-sm text-muted">
              No monitors in this selection. Open an exact report version to choose annotations and
              create a silent baseline.
            </p>
          ) : (
            <ul className="divide-y divide-line">
              {resource.data.items.map((item) => (
                <li key={item.id} className="space-y-1 py-3">
                  <Link
                    className="font-medium text-ember underline"
                    to={annotationMonitorHref(item.id)}
                  >
                    {item.name}
                  </Link>
                  <p className="text-xs text-muted">
                    Version {item.version_number}; {item.status}; checkpoint{' '}
                    {item.checkpoint_number}; notifications {item.notify_on_change ? 'on' : 'off'}.
                  </p>
                  {item.unavailable_reason && (
                    <p className="text-sm">Unavailable: {item.unavailable_reason}</p>
                  )}
                </li>
              ))}
            </ul>
          )}
          <MonitorPagination
            label="monitor"
            offset={offset}
            count={resource.data.items.length}
            total={resource.data.total}
            onChange={setOffset}
          />
        </>
      )}
    </section>
  );
}
