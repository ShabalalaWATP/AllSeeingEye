/**
 * Where each workspace switch returns an administrator: the last research route and the
 * last administration page visited in this tab. Memory only: nothing here is written to
 * browser storage, and it is forgotten whenever the signed-in account changes or signs out.
 * Explicitly requested routes (deep links, post-login destinations) never read it; only
 * the workspace switches and "Return to research" do.
 */
import { create } from 'zustand';

import { useAuthStore } from './auth';

export const RESEARCH_HOME = '/';
export const ADMIN_HOME = '/admin';

const MAX_ROUTE_LENGTH = 2048;

// Public, sign-in and development pages are not part of the research workspace.
const NOT_RESEARCH = [
  '/admin',
  '/login',
  '/request-account',
  '/forgot-password',
  '/set-password',
  '/activate',
  '/reset-password',
  '/privacy',
  '/attributions',
  '/accessibility',
  '/terms',
  '/business',
  '/enterprise',
  '/brand',
  '/dev',
];

export interface WorkspaceReturnState {
  research: string;
  admin: string;
}

const initialWorkspaceReturn: WorkspaceReturnState = { research: RESEARCH_HOME, admin: ADMIN_HOME };

export const useWorkspaceReturnStore = create<WorkspaceReturnState>()(() => ({
  ...initialWorkspaceReturn,
}));

function within(pathname: string, prefix: string): boolean {
  return pathname === prefix || pathname.startsWith(`${prefix}/`);
}

/** Only same-origin, single-slash application paths are ever offered as a target. */
function isAppPath(pathname: string, search: string): boolean {
  return (
    pathname.startsWith('/') &&
    !pathname.startsWith('//') &&
    !pathname.includes('\\') &&
    (search === '' || search.startsWith('?')) &&
    pathname.length + search.length <= MAX_ROUTE_LENGTH
  );
}

export function isResearchRoute(pathname: string, search = ''): boolean {
  return isAppPath(pathname, search) && !NOT_RESEARCH.some((prefix) => within(pathname, prefix));
}

export function isAdminRoute(pathname: string, search = ''): boolean {
  return isAppPath(pathname, search) && within(pathname, ADMIN_HOME);
}

export function rememberResearchRoute(pathname: string, search = ''): void {
  if (!isResearchRoute(pathname, search)) return;
  useWorkspaceReturnStore.setState({ research: `${pathname}${search}` });
}

export function rememberAdminRoute(pathname: string, search = ''): void {
  if (!isAdminRoute(pathname, search)) return;
  useWorkspaceReturnStore.setState({ admin: `${pathname}${search}` });
}

export function resetWorkspaceReturn(): void {
  useWorkspaceReturnStore.setState({ ...initialWorkspaceReturn });
}

// A different account, or none, never inherits the previous account's places.
useAuthStore.subscribe((state, previous) => {
  if (state.user?.id !== previous.user?.id) resetWorkspaceReturn();
});
