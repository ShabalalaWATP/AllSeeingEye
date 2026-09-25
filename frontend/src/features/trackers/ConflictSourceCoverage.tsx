import { fetchConflictSources } from '@/lib/api/trackers';
import { useResource } from '@/lib/hooks/useResource';
import { formatUtc } from '@/lib/format';

const labels = {
  configured: 'Configured',
  waiting: 'Waiting for data',
  not_configured: 'Not configured',
  healthy: 'Healthy',
  degraded: 'Degraded',
};

export function ConflictSourceCoverage() {
  const { data, loading, error, reload } = useResource(fetchConflictSources);
  return (
    <section
      aria-label="Conflict source coverage"
      className="rounded-lg border border-line bg-surface/50 p-4"
    >
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold">Source coverage</h2>
        <button
          type="button"
          onClick={() => {
            void reload();
          }}
          disabled={loading}
          className="min-h-9 px-2 text-xs text-cyan disabled:opacity-50"
        >
          Refresh coverage
        </button>
      </div>
      {loading && <p className="text-xs text-muted">Checking source coverage…</p>}
      {error && (
        <p role="status" className="text-xs text-muted">
          Source coverage is temporarily unavailable. Collected evidence remains accessible.
        </p>
      )}
      {data?.length === 0 && (
        <p className="text-xs text-muted">No source status information returned.</p>
      )}
      {data && (
        <ul className="divide-y divide-line">
          {data.map((source) => (
            <li key={source.id} className="space-y-1 py-3 text-xs">
              <div className="flex flex-wrap justify-between gap-2">
                <span className="font-medium">{source.name}</span>
                <span className={source.status === 'healthy' ? 'text-emerald-300' : 'text-muted'}>
                  {labels[source.status]}
                </span>
              </div>
              <p className="text-muted">
                {source.role} · {source.detail}
              </p>
              {source.id !== 'conflict_screening' && (
                <p className="font-mono text-2xs text-muted">
                  {source.dataset_release ? `Dataset ${source.dataset_release} · ` : ''}Last
                  successful collection:{' '}
                  {source.last_success ? formatUtc(source.last_success) : 'Not yet recorded'}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
      <p className="mt-2 text-[11px] text-muted">
        Source availability, release dates and collection gaps limit what this tracker can show.
      </p>
    </section>
  );
}
