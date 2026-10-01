/**
 * Space a scroll container keeps clear for the fixed Eye launcher, so that a control which
 * receives keyboard focus is not scrolled underneath it (WCAG 2.4.11). At its home position
 * the launcher is LAUNCHER_HEIGHT (82px) tall and sits LAUNCHER_HOME_BOTTOM (28px) above the
 * viewport edge; 7rem (112px) covers both. A launcher dragged elsewhere is the reader's choice,
 * and Home on the launcher returns it here.
 */
export const LAUNCHER_CLEARANCE_PX = 112;

/** For a page's own scroll container: focus scrolling stops above the launcher. */
export const LAUNCHER_SCROLL_PADDING = 'scroll-pb-28';

/** For content inside a scroll container the page does not own. */
export const LAUNCHER_SCROLL_MARGIN = '[&_*]:scroll-mb-28';
