import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import { formatUtc } from '@/lib/format';
import { useResearchAllowance } from '@/lib/hooks/useResearchAllowance';

export function ResearchAllowanceSummary() {
  const { data, loading, error, reload } = useResearchAllowance();
  return (
    <section
      aria-label="Research allowance"
      className="rounded-xl border border-line/70 bg-surface/40 p-4 text-sm"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h2 className="font-semibold">Research allowance</h2>
        <Button variant="ghost" busy={loading} onClick={() => void reload()}>
          Refresh research allowance
        </Button>
      </div>
      {loading && !data && <LoadingNote label="Loading research allowance" />}
      {error && (
        <Alert tone="warning">
          {describeError(error)}{' '}
          <Button variant="ghost" onClick={() => void reload()}>
            Retry research allowance
          </Button>
        </Alert>
      )}
      {data && (
        <div className="mt-2 space-y-2">
          {data.limit === null ? (
            <>
              <p className="font-medium">{data.label} · Unlimited research runs</p>
              <p className="text-xs text-muted">No limit on research runs.</p>
              <p className="text-xs text-muted">
                {data.used} {data.used === 1 ? 'run' : 'runs'} recorded today (UTC)
              </p>
            </>
          ) : (
            <>
              <p className="font-medium">
                {data.remaining} of {data.limit} research runs remaining
              </p>
              <p className="text-xs text-muted">
                {data.label} · {data.limit} runs per {data.period} · Resets{' '}
                {formatUtc(data.resets_at)}
              </p>
              {data.remaining === 0 && (
                <p className="text-amber">
                  Your research allowance is used. New manual and subscription runs can start after
                  the reset.
                </p>
              )}
            </>
          )}
        </div>
      )}
      <p className="mt-3 text-xs leading-5 text-muted">
        {data?.limit === null
          ? 'Manual research and subscription runs are recorded together.'
          : 'Manual research and subscription runs share this allowance.'}{' '}
        Each new report or regeneration counts once, including work that later fails or is
        cancelled. Resuming existing work does not use another run.
      </p>
      <p className="mt-1 text-xs leading-5 text-muted">
        Browsing, map tools and feed refreshes do not count. AI provider limits also apply.
      </p>
    </section>
  );
}
