import { useEffect, useRef } from 'react';

/**
 * Scrolls a region into view and focuses its first field each time `request` increases.
 * Zero means nothing has been requested, so the first render never moves focus.
 */
export function useFocusRequest<T extends HTMLElement>(request: number) {
  const ref = useRef<T>(null);
  useEffect(() => {
    const region = ref.current;
    if (request === 0 || region === null) return;
    // jsdom and some older engines lack scrollIntoView; focusing still brings it on screen.
    if (typeof region.scrollIntoView === 'function') region.scrollIntoView({ block: 'center' });
    region
      .querySelector<HTMLElement>('select, input, textarea, button')
      ?.focus({ preventScroll: true });
  }, [request]);
  return ref;
}
