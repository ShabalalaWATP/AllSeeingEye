/**
 * One name per route, shared by the top bar and the document title. Rail and tracker
 * destinations name themselves; detail pages without a rail entry are listed here.
 */
import { adminLocation } from '@/lib/adminNavigation';
import {
  activeWorkspacePath,
  trackerModules,
  workspaceDestinations,
} from '@/lib/workspaceNavigation';

export const APP_TITLE = 'The All Seeing Eye';

/** Pages reached from another page rather than the rail, most specific first. */
const DETAIL_PAGES: readonly (readonly [RegExp, string])[] = [
  [/^\/research\/saved$/, 'Saved research'],
  [/^\/research\/jobs\/[^/]+$/, 'Research job'],
  [/^\/subscriptions\/saved$/, 'Saved updates'],
  [/^\/geolocation\/saved$/, 'Saved assessments'],
  [/^\/reports\/[^/]+$/, 'Report'],
  [/^\/annotation-monitors\/[^/]+\/transitions\/[^/]+$/, 'Annotation change'],
  [/^\/annotation-monitors\/[^/]+$/, 'Annotation monitor'],
  [/^\/direction\/plans\/[^/]+$/, 'Collection plan'],
  [/^\/trackers\/conflicts\/[^/]+$/, 'Conflict'],
  [/^\/trackers\/disasters\/[^/]+$/, 'Disaster'],
  [/^\/account\/security$/, 'Account security'],
  [/^\/account$/, 'Account'],
  [/^\/settings$/, 'Your settings'],
];

function adminTitle(path: string): string {
  const location = adminLocation(path);
  if (location?.section == null) return 'Administration';
  return `${location.page.label} · Administration`;
}

/** The plain name of the page at `pathname`, or the application name when unknown. */
export function pageTitle(pathname: string): string {
  const path = pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname;
  if (path === '/admin' || path.startsWith('/admin/')) return adminTitle(path);
  const detail = DETAIL_PAGES.find(([pattern]) => pattern.test(path));
  if (detail !== undefined) return detail[1];
  const tracker = trackerModules.find((module) => module.to === path);
  if (tracker !== undefined) return tracker.label;
  const active = activeWorkspacePath(path);
  return workspaceDestinations().find((page) => page.to === active)?.label ?? APP_TITLE;
}

/** "Watches · The All Seeing Eye", or just the application name when the page is unknown. */
export function documentTitle(pathname: string): string {
  const title = pageTitle(pathname);
  return title === APP_TITLE ? APP_TITLE : `${title} · ${APP_TITLE}`;
}
