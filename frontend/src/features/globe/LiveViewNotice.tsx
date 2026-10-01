import type { LiveViewNoticeState } from './useLiveViewOpening';

/** Opening status for a saved view, including what was left out and stale links. */
export function LiveViewNotice({
  notice,
  onClose,
}: {
  notice: LiveViewNoticeState | null;
  onClose: () => void;
}) {
  if (!notice) return null;
  return (
    <aside
      aria-label="Saved live view"
      className="absolute top-28 left-1/2 z-20 flex max-w-[65%] -translate-x-1/2 items-center gap-3 rounded-lg border border-line bg-surface px-4 py-2 text-xs shadow-lg"
    >
      <div role={notice.status === 'unavailable' ? 'alert' : 'status'}>
        {notice.status === 'loading' && <p>Opening saved view…</p>}
        {notice.status === 'unavailable' && (
          <p>This saved view is unavailable or you no longer have access.</p>
        )}
        {notice.status === 'opened' && (
          <>
            <p>
              Opened <strong>{notice.title}</strong>.
            </p>
            {notice.dropped.length > 0 && (
              <p className="text-muted">
                No longer available, so left out: {notice.dropped.join(', ')}.
              </p>
            )}
          </>
        )}
      </div>
      <button
        type="button"
        aria-label="Close saved view notice"
        className="min-h-10 px-2"
        onClick={onClose}
      >
        Close
      </button>
    </aside>
  );
}
