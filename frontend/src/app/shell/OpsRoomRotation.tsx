/** The wall screen's caption and controls while a saved playlist rotates. Loaded lazily. */
import { useEffect, useRef } from 'react';

import { Button } from '@/components/ui/Button';
import { useLiveViewStore } from '@/stores/liveView';
import { useOpsRoomRotation } from './useOpsRoomRotation';

const INTERACTIONS = ['pointerdown', 'wheel', 'touchstart', 'keydown'] as const;

export default function OpsRoomRotation() {
  const playlistId = useLiveViewStore((state) => state.playlistId);
  const rotation = useOpsRoomRotation(playlistId);
  const controls = useRef<HTMLElement>(null);
  const { interact } = rotation;
  useEffect(() => {
    if (!playlistId) return;
    // Touching the map or the keyboard holds the current view; the controls themselves do not.
    const listener = (event: Event) => {
      if (event instanceof KeyboardEvent && event.key === 'Escape') return;
      if (event.target instanceof Node && controls.current?.contains(event.target)) return;
      interact();
    };
    for (const name of INTERACTIONS) window.addEventListener(name, listener, { passive: true });
    return () => {
      for (const name of INTERACTIONS) window.removeEventListener(name, listener);
    };
  }, [playlistId, interact]);
  if (!playlistId) return null;
  const { shown, paused, held } = rotation;
  const stopped = paused || held;
  return (
    <section
      ref={controls}
      aria-label="Ops room rotation"
      className="absolute bottom-20 left-3 z-20 max-w-[min(32rem,calc(100%-1.5rem))] rounded-card border border-line bg-ground/90 px-4 py-3 text-text shadow-lg"
    >
      <p data-testid="ops-room-announcer" aria-live="polite" className="sr-only">
        {shown
          ? `Showing ${String(shown.index + 1)} of ${String(shown.total)}: ${shown.caption}`
          : ''}
      </p>
      {shown ? (
        <>
          <p className="text-lg font-medium leading-snug">{shown.caption}</p>
          <p className="font-mono text-2xs uppercase tracking-[0.2em] text-muted">
            {`${String(shown.index + 1)} of ${String(shown.total)}`}
          </p>
        </>
      ) : (
        <p className="text-sm text-muted">Loading playlist…</p>
      )}
      {stopped && (
        <p className="mt-1 text-xs text-muted">
          {held && !paused ? 'Paused while you interact' : 'Paused'}
        </p>
      )}
      {rotation.skipped && (
        <p aria-live="polite" className="mt-1 text-xs text-muted">
          {rotation.skipped}
        </p>
      )}
      <div className="mt-2 flex flex-wrap gap-2">
        <Button
          variant="ghost"
          className="min-h-11"
          onClick={rotation.previous}
          disabled={!shown}
          aria-label="Previous view"
        >
          Previous
        </Button>
        <Button
          variant="ghost"
          className="min-h-11"
          onClick={stopped ? rotation.resume : rotation.pause}
          aria-label={stopped ? 'Resume rotation' : 'Pause rotation'}
        >
          {stopped ? 'Resume' : 'Pause'}
        </Button>
        <Button
          variant="ghost"
          className="min-h-11"
          onClick={rotation.next}
          disabled={!shown}
          aria-label="Next view"
        >
          Next
        </Button>
        <Button variant="ghost" className="min-h-11" onClick={rotation.stop}>
          Stop rotation
        </Button>
      </div>
    </section>
  );
}
