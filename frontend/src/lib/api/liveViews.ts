/** Live views are map workspace documents of their own kind. */
import { readLiveView, type LiveViewState } from '@/lib/liveViews/liveViewState';
import { workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

import { ApiError } from './errors';
import {
  createMapWorkspaceDocument,
  getMapWorkspaceDocument,
  listMapWorkspaceDocuments,
  removeMapWorkspaceDocument,
  updateMapWorkspaceDocument,
  type MapWorkspaceDocument,
} from './mapWorkspace';

type Kind = 'live_view';

/**
 * Reads discard a result that arrives after the account or workspace access changed. A
 * missing view is an ordinary outcome (a stale or unshared link), so it
 * does not invalidate every other scoped choice the way a rejected mutation does.
 */
async function stableRead<T>(action: () => Promise<T>): Promise<T> {
  const actor = useAuthStore.getState().user?.id;
  const access = workspaceRevision();
  const result = await action();
  if (actor !== useAuthStore.getState().user?.id || access !== workspaceRevision())
    throw new ApiError(409, 'access_changed', 'Account or team access changed.');
  return result;
}

/** A document of another kind behind a view link is treated as unavailable. */
async function getKind(kind: Kind, id: string, signal?: AbortSignal) {
  const document = await stableRead(() => getMapWorkspaceDocument(id, signal));
  if (document.kind !== kind) throw new ApiError(404, 'not_found', 'Not found.');
  return document;
}

export const listLiveViews = (signal?: AbortSignal) =>
  stableRead(() => listMapWorkspaceDocuments('live_view', signal, { limit: 100 }));

export async function getLiveView(id: string, signal?: AbortSignal) {
  const document = await getKind('live_view', id, signal);
  return { document, ...readLiveView(document.payload) };
}

export function saveLiveView(
  view: LiveViewState,
  title: string,
  options: { existing?: MapWorkspaceDocument | null; teamId?: string },
  signal?: AbortSignal,
) {
  const payload = { ...view } as unknown as Record<string, unknown>;
  const { existing, teamId } = options;
  return existing
    ? updateMapWorkspaceDocument(
        existing.id,
        { title, payload, expected_revision: existing.revision },
        signal,
      )
    : createMapWorkspaceDocument(
        { kind: 'live_view', title, payload, ...(teamId ? { team_id: teamId } : {}) },
        signal,
      );
}

export const removeLiveDocument = (id: string, signal?: AbortSignal) =>
  removeMapWorkspaceDocument(id, signal);
