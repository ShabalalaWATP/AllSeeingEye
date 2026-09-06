import { MAX_CLIENT_EVENTS, SNAPSHOT_LIMIT, useEventsStore } from '@/stores/events';

/** Browser coverage differs from the server's retained feed window. */
export function LiveCoverage({ filteredCount }: { filteredCount: number }) {
  const count = useEventsStore((state) => state.list.length);
  const snapshotCount = useEventsStore((state) => state.snapshotCount);
  const limited = useEventsStore((state) => state.snapshotLimited);
  const capped = useEventsStore((state) => state.mirrorCapped);
  const loading = useEventsStore((state) => state.loading);
  const reload = useEventsStore((state) => state.load);
  return (
    <div
      className="mt-2 space-y-1 border-t border-line px-1 pt-2 text-[11px] text-muted"
      aria-label="Live event coverage"
    >
      <p>
        {count.toLocaleString('en-GB')} loaded in this browser;{' '}
        {filteredCount.toLocaleString('en-GB')} in the selected country and time window.
      </p>
      <p>
        Snapshot limit {SNAPSHOT_LIMIT.toLocaleString('en-GB')}; browser limit{' '}
        {MAX_CLIENT_EVENTS.toLocaleString('en-GB')}.
      </p>
      {snapshotCount !== null && (
        <p>
          Last snapshot: {snapshotCount.toLocaleString('en-GB')} records.
          {limited ? ' Partial feed coverage.' : ''}
        </p>
      )}
      {capped && <p>Browser limit reached. Older observed records have been omitted.</p>}
      <p>Layer counts describe loaded records, not independent sources or complete coverage.</p>
      <button
        type="button"
        disabled={loading}
        onClick={() => void reload()}
        className="min-h-9 text-ember underline disabled:opacity-50"
      >
        {loading ? 'Synchronising events...' : 'Reload live events'}
      </button>
    </div>
  );
}
