/**
 * A persistent map banner while replay is on, so a replayed moment is never read as
 * live. It is deliberately not a live region: the cursor moves every playback tick and
 * the Event time panel's announcer already speaks the discrete changes.
 */
import { formatReplayTime } from './useLiveReplay';
import { useReplayStore } from './replayStore';

export function ReplayBanner() {
  const active = useReplayStore((state) => state.active);
  const cursor = useReplayStore((state) => state.cursor);
  const returnToLive = useReplayStore((state) => state.returnToLive);
  if (!active) return null;
  return (
    <section
      aria-label="Replay mode"
      className="absolute top-16 left-1/2 z-20 flex max-w-[calc(100%-1.5rem)] -translate-x-1/2 flex-wrap items-center gap-x-3 gap-y-1 rounded-md border-2 border-ember bg-surface px-3 py-1.5 text-xs shadow-lg md:top-3"
    >
      <strong className="font-semibold tracking-wide text-ember uppercase">Replay, not live</strong>
      <span className="text-text">
        Events up to <span className="font-mono">{formatReplayTime(cursor)}</span>
      </span>
      <button
        type="button"
        className="min-h-10 rounded-sm px-2 font-medium text-ember underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember"
        onClick={() => {
          returnToLive();
        }}
      >
        Return to live
      </button>
    </section>
  );
}
