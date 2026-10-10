import { useId } from 'react';

import EvilEye from '@/components/brand/EvilEye';
import { BRAND_GROUND } from '@/components/brand/tokens';

import { useProductMotionPause } from './motion/useProductMotionPause';
import { useStoryMotion } from './motion/useStoryMotion';

/** The original brand eye, driven by the public story's device-only motion choice. */
export function ProductBrandMark({ size = 26 }: { size?: number }) {
  const motion = useStoryMotion();
  return (
    <div aria-hidden="true" className="shrink-0" style={{ width: size * 1.4, height: size }}>
      <EvilEye
        deferUntilVisible
        workerRendering
        transparent
        scale={0.6}
        pupilFollow={0}
        backgroundColor={BRAND_GROUND}
        maxFps={motion.still ? 1 : 24}
        flameSpeed={motion.still ? 0 : 1}
        paused={motion.idle}
        fallbackSizes={`${size}px`}
      />
    </div>
  );
}

export function ProductMotionToggle() {
  const motion = useProductMotionPause();
  const noteId = useId();
  const note = 'Your device is set to reduce motion. Change that setting to resume animation.';
  return (
    <div className="story-motion">
      <button
        type="button"
        aria-label="Pause animation"
        aria-pressed={motion.paused}
        aria-disabled={motion.systemReduced || undefined}
        aria-describedby={motion.systemReduced ? noteId : undefined}
        title={motion.systemReduced ? note : motion.paused ? 'Resume animation' : 'Pause animation'}
        onClick={motion.toggle}
        className="flex h-7 w-7 items-center justify-center rounded-full border border-line bg-ground/40 text-muted transition-colors hover:border-control-border hover:text-text"
      >
        <svg width="11" height="11" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          {motion.paused ? (
            <path d="M5 3.5v9l7.5-4.5Z" />
          ) : (
            <path d="M4.5 3.5h2.5v9H4.5Zm4.5 0h2.5v9H9Z" />
          )}
        </svg>
      </button>
      {motion.systemReduced && (
        <p id={noteId} className="sr-only">
          {note}
        </p>
      )}
    </div>
  );
}
