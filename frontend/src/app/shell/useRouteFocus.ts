import type { RefObject } from 'react';
import { useLocation } from 'react-router';

import { pageTitle } from './pageTitles';
import { usePageFocus } from './usePageFocus';

export { HEADING_WAIT_MS, focusPage } from './usePageFocus';

/** Signed-in pages derive their default title from the navigation directory. */
export function useRouteFocus(mainRef: RefObject<HTMLElement | null>, title?: string) {
  const { pathname } = useLocation();
  return usePageFocus(mainRef, title ?? pageTitle(pathname));
}
