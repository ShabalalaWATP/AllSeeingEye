import { useRef } from 'react';

import { useRouteFocus } from './useRouteFocus';

/**
 * Pages outside the signed-in shells get the same titles, announcements and focus moves.
 * Render it inside the page's main landmark; it finds that landmark itself so a layout
 * needs no extra wiring. `title` names a page the route title map cannot, such as the
 * not-found page.
 */
export function PublicRouteFocus({ title }: { title?: string }) {
  const mainRef = useRef<HTMLElement | null>(null);
  const announcerRef = useRouteFocus(mainRef, title);
  return (
    <p
      ref={(node) => {
        announcerRef.current = node;
        mainRef.current = node?.closest('main') ?? null;
      }}
      aria-live="polite"
      aria-atomic="true"
      className="sr-only"
    />
  );
}
