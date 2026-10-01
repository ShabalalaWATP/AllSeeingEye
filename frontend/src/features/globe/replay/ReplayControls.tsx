/**
 * Play, pause, step and scrub through the events already held in this browser. Native
 * buttons and a native range input carry the keyboard behaviour; one polite announcer
 * speaks only discrete changes, never each playback tick.
 */
import { MAX_CLIENT_EVENTS } from '@/stores/events';

import { stepOfCursor } from './liveReplay';
import { boundaryMessage, formatReplayTime, type LiveReplay } from './useLiveReplay';

function excludedText(count: number): string {
  return count === 1
    ? '1 event without a usable time is excluded from replay.'
    : `${count.toLocaleString('en-GB')} events without a usable time are excluded from replay.`;
}

export function ReplayControls({ replay }: { replay: LiveReplay }) {
  const { index, cursor, active, playing, boundary, reducedMotion } = replay;
  const position = cursor === null ? 0 : stepOfCursor(index, cursor);
  return (
    <section aria-label="Replay retained events" className="map-tool-section">
      <h3 className="map-tool-section-title">Replay retained events</h3>
      <p className="map-tool-help">
        Replay uses only the events this browser already holds from the live store (at most{' '}
        {MAX_CLIENT_EVENTS.toLocaleString('en-GB')}), within the chosen time window. It makes no new
        requests and cannot show events that have expired. Records are ordered by publication time
        for reporting and acquisition time for observations; retrieval time is never substituted.
      </p>
      {index.excluded > 0 && <p className="map-tool-help">{excludedText(index.excluded)}</p>}
      {!active ? (
        <>
          <button
            type="button"
            className="map-tool-secondary self-start"
            disabled={index.start === null}
            onClick={replay.start}
          >
            Start replay
          </button>
          {index.start === null && (
            <p className="map-tool-help">No retained event has a usable time to replay.</p>
          )}
        </>
      ) : (
        <>
          <p className="text-sm">
            <span className="map-tool-state" data-active="true">
              Replay, not live
            </span>{' '}
            Showing {replay.events.length.toLocaleString('en-GB')} of{' '}
            {index.usable.toLocaleString('en-GB')} timed events up to{' '}
            <span className="font-mono">{formatReplayTime(cursor)}</span>.
          </p>
          <label className="map-tool-field">
            <span>Replay time</span>
            <input
              type="range"
              min={0}
              max={index.steps}
              step={1}
              value={position}
              onChange={(event) => {
                replay.scrub(Number(event.target.value));
              }}
              aria-valuetext={formatReplayTime(cursor)}
              className="h-11 w-full accent-ember"
            />
          </label>
          <div className="map-tool-actions">
            <button
              type="button"
              className="map-tool-secondary"
              onClick={() => {
                replay.step(-1);
              }}
            >
              Step back one hour
            </button>
            <button
              type="button"
              className="map-tool-secondary"
              disabled={reducedMotion}
              onClick={playing ? replay.pause : replay.play}
            >
              {playing ? 'Pause replay' : 'Play replay'}
            </button>
            <button
              type="button"
              className="map-tool-secondary"
              onClick={() => {
                replay.step(1);
              }}
            >
              Step forward one hour
            </button>
            <button
              type="button"
              className="map-tool-text-button"
              onClick={() => {
                replay.stop();
              }}
            >
              Return to live
            </button>
          </div>
          {reducedMotion && (
            <p className="map-tool-help">
              Automatic play is off because reduced motion is requested. Step or move the slider
              instead.
            </p>
          )}
          {boundary !== null && (
            <p className="map-tool-notice">{boundaryMessage(boundary, cursor)}</p>
          )}
        </>
      )}
      <p data-testid="replay-announcer" role="status" aria-live="polite" className="sr-only">
        {replay.announcement}
      </p>
    </section>
  );
}
