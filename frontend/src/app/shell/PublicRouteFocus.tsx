import { useRef } from 'react';

import { usePageFocus } from './usePageFocus';

/**
 * Pages outside the signed-in shells get the same titles, announcements and focus moves.
 * Render it inside the page's main landmark; it finds that landmark itself so a layout
 * needs no extra wiring. Public callers name themselves without the private route map.
 */
export function PublicRouteFocus({ title }: { title: string }) {
  const mainRef = useRef<HTMLElement | null>(null);
  const announcerRef = usePageFocus(mainRef, title);
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
