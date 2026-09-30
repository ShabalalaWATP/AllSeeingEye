/**
 * Pause or resume the animated brand eye. The accessible name stays "Pause animation"
 * and aria-pressed carries the state, so assistive technology hears one stable control.
 */
import { useId } from 'react';

import { useMotionPause } from './useMotionPause';

const SYSTEM_NOTE =
  'Your device is set to reduce motion, so the eye stays still. Change that setting on your device to resume it.';
const FAILED_NOTE = 'Your animation choice was not saved. The eye stays paused for this session.';

export interface MotionToggleProps {
  /** Icon-only presentation for the collapsed rail; the text stays available to screen readers. */
  compact?: boolean;
  /** Presentation for the dark sign-in brand panel. */
  tone?: 'rail' | 'auth';
  className?: string;
}

function MotionGlyph({ paused }: { paused: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="currentColor"
      aria-hidden="true"
      focusable="false"
      className="shrink-0"
    >
      {paused ? <path d="M5 3.5v9l7.5-4.5Z" /> : <path d="M4.5 3.5h2.5v9H4.5Zm4.5 0h2.5v9H9Z" />}
    </svg>
  );
}

export function MotionToggle({
  compact = false,
  tone = 'rail',
  className = '',
}: MotionToggleProps) {
  const motion = useMotionPause();
  const noteId = useId();
  const blocked = motion.systemReduced;
  const state = motion.paused ? 'text-ember' : 'text-muted hover:text-text';
  const shape =
    tone === 'auth'
      ? 'min-h-10 gap-2 rounded-full border border-control-border bg-ground/80 px-3.5 font-mono text-2xs tracking-[0.12em] uppercase'
      : `min-h-10 w-full gap-3 rounded-lg text-xs hover:bg-surface ${compact ? 'justify-center' : 'px-3'}`;
  const noteClass = compact
    ? 'sr-only'
    : `mt-1 text-2xs leading-snug text-muted ${tone === 'auth' ? 'max-w-56 text-right' : 'px-3'}`;

  return (
    <div className={className}>
      <button
        type="button"
        aria-pressed={motion.paused}
        aria-disabled={blocked || motion.saving ? true : undefined}
        aria-describedby={blocked ? noteId : undefined}
        title={compact ? (blocked ? SYSTEM_NOTE : 'Pause animation') : undefined}
        onClick={motion.toggle}
        className={`flex items-center transition-colors ${shape} ${state}`}
      >
        <MotionGlyph paused={motion.paused} />
        <span className={compact ? 'sr-only' : undefined}>Pause animation</span>
      </button>
      {blocked && (
        <p id={noteId} className={noteClass}>
          {SYSTEM_NOTE}
        </p>
      )}
      {motion.failed && (
        <div className={compact ? 'mt-1 flex justify-center' : 'mt-1'}>
          <p role="alert" className={noteClass}>
            {FAILED_NOTE}
          </p>
          <button
            type="button"
            onClick={motion.retry}
            aria-label="Retry saving animation choice"
            className={`min-h-8 rounded-md text-2xs text-ember underline underline-offset-2 hover:text-text ${compact ? 'px-1' : 'px-3'}`}
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
}
