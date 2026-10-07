/**
 * One passive scroll and resize listener and one animation frame for the whole story.
 * Every subscriber measures first and writes afterwards, so a frame reads layout once
 * for all chapters instead of interleaving reads and style writes.
 */

export interface ScrollSubscriber<T> {
  measure: () => T;
  apply: (measured: T) => void;
}

type AnySubscriber = ScrollSubscriber<unknown>;

const subscribers = new Set<AnySubscriber>();
let frame = 0;

function run(): void {
  frame = 0;
  const pending = [...subscribers];
  const measured = pending.map((subscriber) => subscriber.measure());
  pending.forEach((subscriber, index) => subscriber.apply(measured[index]));
}

function schedule(): void {
  if (frame === 0) frame = window.requestAnimationFrame(run);
}

export function subscribeScroll<T>(subscriber: ScrollSubscriber<T>): () => void {
  const entry = subscriber as AnySubscriber;
  if (subscribers.size === 0) {
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule, { passive: true });
  }
  subscribers.add(entry);
  schedule();
  return () => {
    subscribers.delete(entry);
    if (subscribers.size > 0) return;
    window.removeEventListener('scroll', schedule);
    window.removeEventListener('resize', schedule);
    if (frame !== 0) window.cancelAnimationFrame(frame);
    frame = 0;
  };
}

/** How far a pinned section has travelled: 0 as its top meets the viewport top, 1 at its end. */
export function pinnedProgress(top: number, height: number, viewport: number): number {
  const travel = height - viewport;
  if (travel <= 0) return top <= 0 ? 1 : 0;
  return clamp01(-top / travel);
}

/** How far an element has crossed the viewport: 0 entering at the bottom, 1 leaving at the top. */
export function passProgress(top: number, height: number, viewport: number): number {
  return clamp01((viewport - top) / (viewport + height));
}

export function clamp01(value: number): number {
  if (Number.isNaN(value)) return 0;
  return Math.min(1, Math.max(0, value));
}

/** Map a progress window [start, end] onto 0..1, for staged beats inside one chapter. */
export function segment(progress: number, start: number, end: number): number {
  if (end <= start) return progress >= end ? 1 : 0;
  return clamp01((progress - start) / (end - start));
}

export function subscriberCount(): number {
  return subscribers.size;
}
