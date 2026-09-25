import { useEffect, useRef, type RefObject } from 'react';
import { NavigationType, useLocation, useNavigationType } from 'react-router';

import { APP_TITLE, documentTitle, pageTitle } from './pageTitles';

/** How long a lazily loaded page may take to render its heading before focus stays on main. */
export const HEADING_WAIT_MS = 5_000;

function focusHeading(heading: HTMLElement): void {
  if (!heading.hasAttribute('tabindex')) heading.tabIndex = -1;
  // A heading is not a control, so programmatic focus needs no visible ring.
  heading.classList.add('focus:outline-none');
  heading.focus({ preventScroll: true });
}

/**
 * Moves focus to the new page's main heading, or to the main landmark until one renders.
 * Focus is never taken back once the reader has moved it elsewhere. Returns a stop hook.
 */
export function focusPage(main: HTMLElement): () => void {
  const heading = () => main.querySelector<HTMLElement>('h1');
  const ready = heading();
  if (ready !== null) {
    focusHeading(ready);
    return () => undefined;
  }
  main.focus({ preventScroll: true });
  const observer = new MutationObserver(() => {
    const late = heading();
    if (late === null) return;
    observer.disconnect();
    if (document.activeElement === main) focusHeading(late);
  });
  observer.observe(main, { childList: true, subtree: true });
  const timer = window.setTimeout(() => {
    observer.disconnect();
  }, HEADING_WAIT_MS);
  return () => {
    observer.disconnect();
    window.clearTimeout(timer);
  };
}

/**
 * Names every route in the document title and, after a client-side route change, moves
 * focus into the new page and announces it through the returned polite live region.
 * The first render of a page load is left alone. Redirects are announced but keep focus
 * where it was, since the reader did not choose them. Search-only changes do nothing.
 */
export function useRouteFocus(
  mainRef: RefObject<HTMLElement | null>,
): RefObject<HTMLParagraphElement | null> {
  const { pathname } = useLocation();
  const navigationType = useNavigationType();
  const announcerRef = useRef<HTMLParagraphElement>(null);
  const previous = useRef<string | null>(null);
  const pending = useRef<() => void>(() => undefined);

  useEffect(() => {
    document.title = documentTitle(pathname);
  }, [pathname]);

  useEffect(() => {
    const work = pending;
    const seen = previous;
    return () => {
      work.current();
      // A remount (development double effects, or returning to this shell) starts afresh.
      seen.current = null;
      document.title = APP_TITLE;
    };
  }, []);

  useEffect(() => {
    const first = previous.current === null;
    const changed = previous.current !== pathname;
    previous.current = pathname;
    // Entering a shell by navigation (from sign-in or the other shell) is a route change too.
    if (first ? navigationType === NavigationType.Pop : !changed) return;
    pending.current();
    const region = announcerRef.current;
    if (region !== null) region.textContent = '';
    let stop: () => void = () => undefined;
    const timer = window.setTimeout(() => {
      if (region !== null) region.textContent = `Navigated to ${pageTitle(pathname)}`;
      if (navigationType !== NavigationType.Replace && mainRef.current !== null)
        stop = focusPage(mainRef.current);
    }, 0);
    pending.current = () => {
      window.clearTimeout(timer);
      stop();
    };
  }, [mainRef, navigationType, pathname]);

  return announcerRef;
}
