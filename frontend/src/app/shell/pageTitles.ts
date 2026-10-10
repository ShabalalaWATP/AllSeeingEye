/**
 * One name per route, shared by the top bar and the document title. Rail destinations,
 * saved views and trackers name themselves from the navigation definition; detail pages
 * without an entry there are listed here.
 */
import { adminLocation } from '@/lib/adminNavigation';
import {
  activeWorkspacePath,
  helpDestination,
  savedViews,
  trackerModules,
  workspaceDestinations,
} from '@/lib/workspaceNavigation';

import { APP_TITLE, withAppTitle } from './documentTitle';
export { APP_TITLE, NOT_FOUND_TITLE, withAppTitle } from './documentTitle';

/** Account pages reached before signing in. */
const PUBLIC_PAGES: ReadonlyMap<string, string> = new Map([
  ['/login', 'Sign in'],
  ['/request-account', 'Request an account'],
  ['/forgot-password', 'Forgotten password'],
  ['/set-password', 'Set your password'],
]);

/** Pages reached from another page rather than the rail, most specific first. */
const DETAIL_PAGES: readonly (readonly [RegExp, string])[] = [
  [/^\/research\/jobs\/[^/]+$/, 'Research job'],
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
  const publicPage = PUBLIC_PAGES.get(path);
  if (publicPage !== undefined) return publicPage;
  const detail = DETAIL_PAGES.find(([pattern]) => pattern.test(path));
  if (detail !== undefined) return detail[1];
  if (path === helpDestination.to) return helpDestination.label;
  const saved = savedViews().find((view) => view.to === path);
  if (saved !== undefined) return saved.label;
  const tracker = trackerModules.find((module) => module.to === path);
  if (tracker !== undefined) return tracker.label;
  const active = activeWorkspacePath(path);
  return workspaceDestinations().find((page) => page.to === active)?.label ?? APP_TITLE;
}

/** The document title for `pathname`, or just the application name when the page is unknown. */
export function documentTitle(pathname: string): string {
  return withAppTitle(pageTitle(pathname));
}
