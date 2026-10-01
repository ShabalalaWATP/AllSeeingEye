/** Saved live views for the panel: bounded list, save with a revision guard, delete. */
import { useCallback, useEffect, useRef, useState } from 'react';

import { describeError, isApiError } from '@/lib/api/errors';
import { listLiveViews, removeLiveDocument, saveLiveView } from '@/lib/api/liveViews';
import type { MapWorkspaceDocument } from '@/lib/api/mapWorkspace';
import { useAbortableScopedResource } from '@/lib/hooks/useScopedResource';
import type { LiveViewState } from '@/lib/liveViews/liveViewState';
import { subscribeWorkspaceAccess } from '@/lib/workspaceAccess';

export function useLiveViewLibrary() {
  const list = useAbortableScopedResource(listLiveViews);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const request = useRef<AbortController | null>(null);
  const items = list.data ?? [];
  const active = items.find((item) => item.id === activeId) ?? null;
  const { setData } = list;

  useEffect(() => {
    const reset = () => {
      request.current?.abort();
      setActiveId(null);
      setError(null);
      setNotice(null);
      setBusy(false);
    };
    const off = subscribeWorkspaceAccess(reset);
    return () => {
      request.current?.abort();
      off();
    };
  }, []);

  const run = useCallback(async (work: (signal: AbortSignal) => Promise<void>) => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await work(controller.signal);
    } catch (caught) {
      if (controller.signal.aborted) return;
      setError(
        isApiError(caught) && caught.status === 409
          ? 'This view changed elsewhere or access changed. Refresh the list before updating it.'
          : describeError(caught),
      );
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }, []);

  return {
    items,
    active,
    busy: busy || list.loading,
    error: error ?? (list.error ? describeError(list.error) : null),
    notice,
    refresh: () => void list.reload(),
    select: (document: MapWorkspaceDocument | null) => setActiveId(document?.id ?? null),
    save: (view: LiveViewState, title: string, update: boolean, teamId?: string) =>
      run(async (signal) => {
        const saved = await saveLiveView(
          view,
          title.trim(),
          { existing: update ? active : null, ...(teamId ? { teamId } : {}) },
          signal,
        );
        if (signal.aborted) return;
        setData((previous) => [saved, ...(previous ?? []).filter((item) => item.id !== saved.id)]);
        setActiveId(saved.id);
        setNotice(`Saved ${saved.title} (revision ${saved.revision}).`);
      }),
    remove: (document: MapWorkspaceDocument) =>
      run(async (signal) => {
        await removeLiveDocument(document.id, signal);
        if (signal.aborted) return;
        setData((previous) => (previous ?? []).filter((item) => item.id !== document.id));
        setNotice(`Deleted ${document.title}.`);
      }),
  };
}

export type LiveViewLibrary = ReturnType<typeof useLiveViewLibrary>;
