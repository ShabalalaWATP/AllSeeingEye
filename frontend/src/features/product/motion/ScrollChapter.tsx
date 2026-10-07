/**
 * A story chapter. Pinned chapters are tall sections whose stage sticks to the
 * viewport while the reader scrolls through `length` screens. Where pinning does not
 * suit the screen (tall content on a small display), the chapter plays the same
 * motion as it passes through the viewport instead. Progress (0..1) is written
 * straight to the `--progress` custom property, so CSS-driven motion never re-renders
 * React; `onStep` reports a discrete beat only when it changes. When the story is
 * still, the chapter is ordinary height and shows its end state.
 */
import { useEffect, useRef, useSyncExternalStore, type ReactNode } from 'react';

import { passProgress, pinnedProgress, segment, subscribeScroll } from './scrollScheduler';
import { useStoryMotion } from './useStoryMotion';

const ROOMY = '(min-width: 900px) and (min-height: 700px)';

function subscribeRoomy(onChange: () => void): () => void {
  if (typeof window.matchMedia !== 'function') return () => undefined;
  const query = window.matchMedia(ROOMY);
  query.addEventListener('change', onChange);
  return () => query.removeEventListener('change', onChange);
}

function readRoomy(): boolean {
  return typeof window.matchMedia === 'function' ? window.matchMedia(ROOMY).matches : true;
}

export interface ScrollChapterProps {
  id: string;
  /** The name announced for the section landmark. */
  label: string;
  /** Screens of scroll the stage stays pinned for; omit for an ordinary section. */
  length?: number;
  /** False plays the motion as the chapter passes, never pinning (tall content). */
  pin?: boolean;
  /** Also pin on small screens; only for stages designed to fit a phone. */
  pinNarrow?: boolean;
  /** Number of discrete beats; `onStep` receives 0..steps-1. */
  steps?: number;
  onStep?: (step: number) => void;
  /** Continuous progress, for canvases and text that draw their own frames. */
  onProgress?: (progress: number) => void;
  className?: string;
  children: ReactNode;
}

export function ScrollChapter({
  id,
  label,
  length,
  pin = true,
  pinNarrow = false,
  steps = 1,
  onStep,
  onProgress,
  className = '',
  children,
}: ScrollChapterProps) {
  const { still } = useStoryMotion();
  const roomy = useSyncExternalStore(subscribeRoomy, readRoomy, () => true);
  const sectionRef = useRef<HTMLElement>(null);
  const stepRef = useRef(-1);
  const callbacks = useRef({ onStep, onProgress });
  useEffect(() => {
    callbacks.current = { onStep, onProgress };
  });
  const animated = length !== undefined && !still;
  const pinned = animated && pin && (roomy || pinNarrow);

  useEffect(() => {
    const section = sectionRef.current;
    if (section === null) return undefined;
    stepRef.current = -1;
    const report = (progress: number) => {
      section.style.setProperty('--progress', progress.toFixed(4));
      callbacks.current.onProgress?.(progress);
      const step = Math.min(steps - 1, Math.floor(progress * steps));
      if (step !== stepRef.current) {
        stepRef.current = step;
        callbacks.current.onStep?.(step);
      }
    };
    if (!animated) {
      report(1);
      return undefined;
    }
    return subscribeScroll({
      measure: () => {
        const rect = section.getBoundingClientRect();
        if (!pinned) {
          return segment(passProgress(rect.top, rect.height, window.innerHeight), 0.05, 0.5);
        }
        // The stuck stage's own height (in svh), not innerHeight, which grows when a
        // mobile address bar collapses and would end the chapter before it unsticks.
        const stage = section.firstElementChild;
        const stageHeight = stage instanceof HTMLElement ? stage.offsetHeight : window.innerHeight;
        return pinnedProgress(rect.top, rect.height, stageHeight);
      },
      apply: report,
    });
  }, [animated, pinned, steps]);

  const mode = pinned ? 'pinned' : animated ? 'passing' : 'still';
  return (
    <section
      ref={sectionRef}
      id={id}
      aria-label={label}
      data-mode={mode}
      className={`story-chapter ${className}`}
      style={pinned ? { height: `${(length + 1) * 100}svh` } : undefined}
    >
      <div className={pinned ? 'story-stage story-stage-pinned' : 'story-stage'}>{children}</div>
    </section>
  );
}
