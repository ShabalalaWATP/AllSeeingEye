/**
 * Controls under the stage: step back and forward, a scrubber that carries the whole journey,
 * and a pause for the ambient motion. Everything here is a native control, so the keyboard and
 * touch behaviour is the browser's own.
 */
import type { JourneyStop } from './journey';

export function JourneyControls({
  stops,
  index,
  onIndex,
  playing,
  onPlaying,
  showPlay,
}: {
  stops: JourneyStop[];
  index: number;
  onIndex: (index: number) => void;
  playing: boolean;
  onPlaying: (playing: boolean) => void;
  showPlay: boolean;
}) {
  const last = Math.max(stops.length - 1, 0);
  const current = stops[index];
  const button =
    'min-h-11 min-w-11 rounded border border-line px-3 text-xs text-muted hover:border-cyan hover:text-text disabled:opacity-40 disabled:hover:border-line disabled:hover:text-muted';
  return (
    <div className="flex flex-wrap items-center gap-2 border-t border-line bg-surface px-3 py-2">
      <button
        type="button"
        className={button}
        onClick={() => onIndex(index - 1)}
        disabled={index <= 0}
      >
        Previous event
      </button>
      <button
        type="button"
        className={button}
        onClick={() => onIndex(index + 1)}
        disabled={index >= last}
      >
        Next event
      </button>
      <label className="flex min-w-[10rem] flex-1 items-center gap-2 text-xs text-muted">
        <span className="sr-only">Journey position</span>
        <input
          type="range"
          min={0}
          max={last}
          step={1}
          value={index}
          onChange={(event) => onIndex(Number(event.target.value))}
          aria-valuetext={current ? `${current.date}, ${current.event.title}` : undefined}
          className="h-11 w-full accent-ember"
        />
      </label>
      <span className="font-mono text-[11px] text-muted">
        {stops.length === 0 ? '0 of 0' : `${index + 1} of ${stops.length}`}
      </span>
      {showPlay ? (
        <button
          type="button"
          className={button}
          aria-pressed={!playing}
          onClick={() => onPlaying(!playing)}
        >
          {playing ? 'Pause motion' : 'Resume motion'}
        </button>
      ) : null}
    </div>
  );
}
