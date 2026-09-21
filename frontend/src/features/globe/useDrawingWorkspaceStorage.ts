import { useEffect, useLayoutEffect, useRef, useState } from 'react';
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
import {
  emptyDrawingCollection,
  validateDrawingCollection,
  type DrawingCollection,
} from '@/lib/map/drawingCollection';

type Document = Awaited<ReturnType<typeof getMapWorkspaceDocument>>;
class DrawingStorageError extends Error {}
const contentKey = (collection: DrawingCollection, title: string) =>
  JSON.stringify([collection.objects, title.trim()]);
export function useDrawingWorkspaceStorage(
  collection: DrawingCollection,
  onLoad: (value: DrawingCollection) => void,
  pendingEdits = false,
  sketchKey = '',
) {
  const [active, setActive] = useState<Document | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [nextOffset, setNextOffset] = useState(0);
  const [title, setTitle] = useState('Map drawings');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [savedKey, setSavedKey] = useState(() =>
    contentKey(emptyDrawingCollection, 'Map drawings'),
  );
  const [pendingLoad, setPendingLoad] = useState<string | null>(null);
  const currentKey = contentKey(collection, title);
  const dirty = pendingEdits || currentKey !== savedKey;
  // Include geometry, not just a dirty boolean: a second edit must invalidate a pending read.
  const editKey = JSON.stringify([currentKey, sketchKey, pendingEdits]);
  const latestEdit = useRef(editKey);
  const revision = useRef(0);
  useLayoutEffect(() => {
    if (latestEdit.current !== editKey) revision.current++;
    latestEdit.current = editKey;
  }, [editKey]);
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
      setPendingLoad(null);
      setSavedKey(contentKey(emptyDrawingCollection, 'Map drawings'));
      revision.current++;
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
      if (!controller.signal.aborted)
        setError(caught instanceof DrawingStorageError ? caught.message : describeError(caught));
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
  const ensureUnchanged = (expected: number) => {
    if (revision.current !== expected)
      throw new DrawingStorageError(
        'Your drawings changed while saving or loading. Your current work is kept; open the collection again when ready.',
      );
  };
  const read = async (id: string, signal: AbortSignal, expected: number) => {
    const result = await scopedMutation(() => getMapWorkspaceDocument(id, signal));
    if (signal.aborted) return;
    ensureUnchanged(expected);
    if (result.kind !== 'drawings') throw new Error('This document is not a drawing collection.');
    const validated = validateDrawingCollection(result.payload);
    onLoad(validated);
    setActive(result);
    setTitle(result.title);
    setSavedKey(contentKey(validated, result.title));
    setPendingLoad(null);
    setNotice('Collection loaded.');
  };
  const persist = async (signal: AbortSignal, copy = false, teamId?: string) => {
    if (pendingEdits)
      throw new DrawingStorageError(
        'Add the sketch to the collection or apply its edits before saving.',
      );
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
      // Only the captured content was saved; edits made during the request remain dirty.
      setSavedKey(contentKey(collection, title));
      setNotice(`Saved revision ${result.revision}.`);
    }
  };
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
    dirty,
    pendingLoad,
    cancelLoad: () => setPendingLoad(null),
    confirmLoad: (decision: 'save' | 'discard', teamId?: string) =>
      run(async (signal) => {
        if (!pendingLoad) return;
        const expected = revision.current;
        if (decision === 'save') await persist(signal, false, teamId);
        if (signal.aborted) return;
        ensureUnchanged(expected);
        await read(pendingLoad, signal, expected);
      }),
    browse: () => browse(),
    loadMore: () => browse(true),
    load: async (id: string) => {
      if (dirty) {
        setPendingLoad(id);
        return;
      }
      const expected = revision.current;
      await run((signal) => read(id, signal, expected));
    },
    save: (copy = false, teamId?: string) => run((signal) => persist(signal, copy, teamId)),
  };
}
