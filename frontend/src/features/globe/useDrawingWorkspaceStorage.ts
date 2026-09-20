import { useEffect, useRef, useState } from 'react';
import {
  createMapWorkspaceDocument,
  getMapWorkspaceDocument,
  listMapWorkspaceDocuments,
  updateMapWorkspaceDocument,
} from '@/lib/api/mapWorkspace';
import { scopedMutation, subscribeWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { describeError } from '@/lib/api/errors';
import { drawingAuthority } from '@/lib/map/drawingAuthority';
import { validateDrawingCollection, type DrawingCollection } from '@/lib/map/drawingCollection';

type Document = Awaited<ReturnType<typeof getMapWorkspaceDocument>>;
export function useDrawingWorkspaceStorage(
  collection: DrawingCollection,
  onLoad: (value: DrawingCollection) => void,
  pendingEdits = false,
) {
  const [active, setActive] = useState<Document | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [nextOffset, setNextOffset] = useState(0);
  const [title, setTitle] = useState('Map drawings');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const request = useRef<AbortController | null>(null);
  useEffect(() => {
    const reset = () => {
      request.current?.abort();
      setActive(null);
      setDocuments([]);
      setHasMore(false);
      setNextOffset(0);
      setTitle('Map drawings');
      setError(null);
      setNotice(null);
      setBusy(false);
    };
    const offAccess = subscribeWorkspaceAccess(reset);
    const offUser = useAuthStore.subscribe((next, previous) => {
      if (drawingAuthority(next) !== drawingAuthority(previous)) reset();
    });
    return () => {
      request.current?.abort();
      offAccess();
      offUser();
    };
  }, []);
  const run = async (work: (signal: AbortSignal) => Promise<void>) => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await work(controller.signal);
    } catch (caught) {
      if (!controller.signal.aborted) setError(describeError(caught));
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  };
  const browse = (more = false) =>
    run(async (signal) => {
      const offset = more ? nextOffset : 0;
      if (!more) {
        setDocuments([]);
        setHasMore(false);
        setNextOffset(0);
      }
      const result = await scopedMutation(() =>
        listMapWorkspaceDocuments('drawings', signal, { offset, limit: 100 }),
      );
      if (signal.aborted) return;
      setDocuments((previous) =>
        Array.from(
          new Map([...(more ? previous : []), ...result].map((item) => [item.id, item])).values(),
        ),
      );
      setNextOffset(offset + result.length);
      setHasMore(result.length === 100);
    });
  return {
    active,
    pendingEdits,
    documents,
    hasMore,
    title,
    setTitle,
    busy,
    error,
    notice,
    browse: () => browse(),
    loadMore: () => browse(true),
    load: (id: string) =>
      run(async (signal) => {
        const result = await scopedMutation(() => getMapWorkspaceDocument(id, signal));
        if (signal.aborted) return;
        if (result.kind !== 'drawings')
          throw new Error('This document is not a drawing collection.');
        const validated = validateDrawingCollection(result.payload);
        onLoad(validated);
        setActive(result);
        setTitle(result.title);
        setNotice('Collection loaded.');
      }),
    save: (copy = false, teamId?: string) =>
      run(async (signal) => {
        if (pendingEdits) {
          setError('Add the sketch to the collection or apply its edits before saving.');
          return;
        }
        const payload = { ...validateDrawingCollection(collection) };
        const result = await scopedMutation(() =>
          active && !copy
            ? updateMapWorkspaceDocument(
                active.id,
                { title: title.trim(), payload, expected_revision: active.revision },
                signal,
              )
            : createMapWorkspaceDocument(
                {
                  title: title.trim(),
                  kind: 'drawings',
                  payload,
                  ...(teamId ? { team_id: teamId } : {}),
                },
                signal,
              ),
        );
        if (!signal.aborted) {
          setActive(result);
          setNotice(`Saved revision ${result.revision}.`);
        }
      }),
  };
}
