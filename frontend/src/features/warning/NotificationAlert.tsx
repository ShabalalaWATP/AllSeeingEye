import { useCallback } from 'react';
import { useSearchParams } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { apiCall } from '@/lib/api/client';
import { alertSchema } from '@/lib/api/warning';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

/** Push contains only an ID. Details are read by the ordinary authenticated app. */
export function NotificationAlert() {
  const [params] = useSearchParams();
  const id = params.get('alert');
  const valid = id !== null && /^[0-9a-f-]{36}$/i.test(id);
  const resource = useScopedResource(
    useCallback(
      async () =>
        valid
          ? apiCall(`/api/warning/alerts/${encodeURIComponent(id)}`, { schema: alertSchema })
          : null,
      [id, valid],
    ),
  );
  if (!valid) return null;
  return (
    <section
      aria-label="Opened notification"
      className="rounded-card border border-line bg-surface p-4"
    >
      {resource.loading && <LoadingNote label="Loading the alert securely…" />}
      {resource.error !== null && (
        <Alert tone="warning">This alert is unavailable or your access has changed.</Alert>
      )}
      {resource.data && (
        <>
          <h2 className="font-semibold">{resource.data.title}</h2>
          <p className="mt-2 text-sm">{resource.data.summary}</p>
        </>
      )}
    </section>
  );
}
