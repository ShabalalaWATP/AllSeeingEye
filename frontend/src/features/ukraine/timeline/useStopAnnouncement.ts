/**
 * Names the journey's new stop through a polite live region: the stop's title and nothing
 * more, once travel has rested on it. A fast wheel, swipe or held key across several stops
 * ends in one announcement rather than a queue of them, and the stop the journey opens on is
 * not announced because its card is already on the page. When the focused control already
 * says the title (the scrubber's value text, or an entry in the reading list), the region
 * stays quiet so the reader hears it once.
 */
import { useEffect, useRef, type RefObject } from 'react';

/** How long travel must rest on a stop before its title is read out. */
export const ANNOUNCE_SETTLE_MS = 400;

/** What the focused control already says aloud, or nothing when focus rests on the page. */
function focusedSpeech(): string {
  const focused = document.activeElement;
  if (!(focused instanceof HTMLElement) || focused === document.body) return '';
  return focused.getAttribute('aria-valuetext') ?? focused.textContent;
}

/** Returns the ref for an empty `aria-live="polite"` element that this hook writes into. */
export function useStopAnnouncement(
  stopId: string | undefined,
  title: string,
): RefObject<HTMLParagraphElement | null> {
  const regionRef = useRef<HTMLParagraphElement | null>(null);
  const announced = useRef(stopId);

  useEffect(() => {
    if (stopId === undefined || stopId === announced.current) return undefined;
    const timer = setTimeout(() => {
      announced.current = stopId;
      const region = regionRef.current;
      if (region === null || focusedSpeech().includes(title)) return;
      region.textContent = title;
    }, ANNOUNCE_SETTLE_MS);
    return () => {
      clearTimeout(timer);
    };
  }, [stopId, title]);

  return regionRef;
}
