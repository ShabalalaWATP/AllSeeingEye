/**
 * A horizontal track of panels. While its chapter is pinned, vertical scroll moves the
 * track sideways as a transform (offsets measured on resize only, never per frame);
 * otherwise the track is a native swipe row inside its viewport. Previous, next and
 * the arrow keys move one panel at a time in either mode: pinned, by scrolling the
 * window to the panel's share of the chapter's progress; unpinned, by scrolling the
 * viewport to the panel. Panel `i` is fully in view at progress i / (count - 1).
 */
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
} from 'react';

import { useStoryMotion } from './useStoryMotion';

function pinnedSection(element: Element): HTMLElement | null {
  return element.closest<HTMLElement>('[data-mode="pinned"]');
}

/** The panel nearest the viewport's scroll position; the end of the row is the last. */
function nearestPanel(viewport: HTMLElement, track: HTMLElement): number {
  const panels = [...track.children].filter((panel) => panel instanceof HTMLElement);
  const max = viewport.scrollWidth - viewport.clientWidth;
  if (max > 0 && viewport.scrollLeft >= max - 2) return Math.max(0, panels.length - 1);
  let nearest = 0;
  panels.forEach((panel, index) => {
    const best = panels[nearest];
    if (
      best !== undefined &&
      Math.abs(panel.offsetLeft - viewport.scrollLeft) <
        Math.abs(best.offsetLeft - viewport.scrollLeft)
    )
      nearest = index;
  });
  return nearest;
}

export function useHorizontalPin(count: number) {
  const { still } = useStoryMotion();
  const trackRef = useRef<HTMLDivElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const travelRef = useRef(0);
  const indexRef = useRef(0);
  const [index, setIndexState] = useState(0);
  const last = Math.max(0, count - 1);

  const setIndex = useCallback((next: number) => {
    if (next === indexRef.current) return;
    indexRef.current = next;
    setIndexState(next);
  }, []);

  useEffect(() => {
    const track = trackRef.current;
    const viewport = viewportRef.current;
    if (track === null || viewport === null) return undefined;
    const measure = () => {
      travelRef.current = Math.max(0, track.scrollWidth - viewport.clientWidth);
    };
    measure();
    if (typeof ResizeObserver !== 'function') return undefined;
    const observer = new ResizeObserver(measure);
    observer.observe(track);
    observer.observe(viewport);
    return () => observer.disconnect();
  }, []);

  // Swipes and native scrolling of the unpinned row keep the position in step.
  useEffect(() => {
    const track = trackRef.current;
    const viewport = viewportRef.current;
    if (still || track === null || viewport === null) return undefined;
    let frame = 0;
    const follow = () => {
      frame = 0;
      if (pinnedSection(viewport) === null) setIndex(nearestPanel(viewport, track));
    };
    const onScroll = () => {
      if (frame === 0) frame = window.requestAnimationFrame(follow);
    };
    viewport.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      viewport.removeEventListener('scroll', onScroll);
      if (frame !== 0) window.cancelAnimationFrame(frame);
    };
  }, [still, setIndex]);

  const onProgress = useCallback(
    (progress: number) => {
      const track = trackRef.current;
      if (track === null) return;
      const pinned = pinnedSection(track) !== null;
      track.style.transform = pinned
        ? `translate3d(${(-progress * travelRef.current).toFixed(1)}px,0,0)`
        : '';
      if (pinned) setIndex(Math.round(progress * last));
    },
    [last, setIndex],
  );

  const goTo = useCallback(
    (target: number) => {
      const next = Math.max(0, Math.min(last, target));
      const track = trackRef.current;
      const viewport = viewportRef.current;
      if (track === null || viewport === null) return;
      setIndex(next);
      const behavior: ScrollBehavior = still ? 'auto' : 'smooth';
      const section = pinnedSection(track);
      if (section !== null) {
        const rect = section.getBoundingClientRect();
        const stage = section.firstElementChild;
        const stageHeight = stage instanceof HTMLElement ? stage.offsetHeight : window.innerHeight;
        const share = last > 0 ? next / last : 0;
        const top = rect.top + window.scrollY + share * Math.max(0, rect.height - stageHeight);
        window.scrollTo({ top: Math.round(top), behavior });
        return;
      }
      const panel = track.children[next];
      if (panel instanceof HTMLElement) viewport.scrollTo({ left: panel.offsetLeft, behavior });
    },
    [last, still, setIndex],
  );

  const onKeyDown = useCallback(
    (event: ReactKeyboardEvent<HTMLElement>) => {
      const step = event.key === 'ArrowLeft' ? -1 : event.key === 'ArrowRight' ? 1 : 0;
      if (step === 0) return;
      event.preventDefault();
      goTo(indexRef.current + step);
    },
    [goTo],
  );

  return { trackRef, viewportRef, index, last, goTo, onProgress, onKeyDown };
}
