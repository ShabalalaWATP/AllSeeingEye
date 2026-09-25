import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import type { PlatformConnection } from '@/lib/api/sourceContext';
import type { ApiError } from '@/lib/api/errors';
import { ConnectionBadge } from './ConnectionBadge';

const KIND_LABELS: Record<PlatformConnection['requirement']['kind'], string> = {
  api_key: 'API key',
  credentials: 'Credentials',
  acknowledgement: 'Acknowledgement',
  snapshot: 'Local snapshot',
  catalogue: 'Local catalogue',
  runtime: 'Local runtime',
  model: 'AI connection',
  toggle: 'Setting',
  endpoint: 'Endpoint',
};

/** Keyed services that are not sources: the model, maps, mail, encryption and tooling. */
export function PlatformConnections({
  data,
  loading,
  error,
  onRetry,
}: {
  data: readonly PlatformConnection[] | null;
  loading: boolean;
  error: ApiError | null;
  onRetry: () => void;
}) {
  return (
    <section aria-label="Platform connections" className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">Platform connections</h2>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">
          Services the app needs beyond public feeds. A missing key is shown here with the server
          setting that unlocks it; values are never displayed. Administrators change these on the
          server or under Admin.
        </p>
      </div>
      {loading && !data && <LoadingNote label="Checking platform connections" />}
      {error && (
        <Alert tone="error">
          {describeError(error)}{' '}
          <Button variant="ghost" onClick={onRetry}>
            Retry connections
          </Button>
        </Alert>
      )}
      {data && (
        <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {data.map((item) => (
            <li
              key={item.id}
              className="flex flex-col gap-2 rounded-xl border border-line/70 bg-surface/60 p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-sm font-semibold">{item.name}</h3>
                <ConnectionBadge state={item.state} optional={item.requirement.optional} />
              </div>
              <p className="text-xs leading-5 text-muted">{item.purpose}</p>
              <p className="text-xs leading-5 text-text/90">{item.requirement.note}</p>
              <p className="mt-auto flex flex-wrap gap-x-3 gap-y-1 pt-1 font-mono text-2xs text-muted">
                <span>{KIND_LABELS[item.requirement.kind]}</span>
                {item.requirement.setting && <span>{item.requirement.setting}</span>}
                <span>{item.detail}</span>
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
