import { useEffect, useRef, useState } from 'react';
import {
  listMapWorkspaceDocuments,
  createMapWorkspaceDocument,
  updateMapWorkspaceDocument,
  removeMapWorkspaceDocument,
} from '@/lib/api/mapWorkspace';
import { parseRfStudy, type RfStudySnapshot } from '@/lib/map/rfStudy';
import { subscribeRfWorkspaceReset } from '@/lib/map/rfWorkspaceAccess';

export interface SavedRadioStudy {
  id: string;
  title: string;
  revision: number;
  teamId: string | null;
  snapshot: RfStudySnapshot;
}
export function useRfStudyLibrary() {
  const [items, setItems] = useState<SavedRadioStudy[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const nextOffset = useRef(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const active = useRef<AbortController | null>(null);
  useEffect(() => {
    const clear = () => {
      active.current?.abort();
      active.current = null;
      setItems([]);
      nextOffset.current = 0;
      setHasMore(false);
      setBusy(false);
      setMessage(null);
    };
    const unsubscribe = subscribeRfWorkspaceReset(clear);
    return () => {
      active.current?.abort();
      unsubscribe();
    };
  }, []);
  const run = async (action: (signal: AbortSignal) => Promise<void>) => {
    active.current?.abort();
    const request = new AbortController();
    active.current = request;
    setBusy(true);
    setMessage(null);
    try {
      await action(request.signal);
    } catch (error) {
      if (!request.signal.aborted)
        setMessage(error instanceof Error ? error.message : 'The radio library request failed.');
    } finally {
      if (!request.signal.aborted) setBusy(false);
    }
  };
  const list = async (signal: AbortSignal, append = false) => {
    const offset = append ? nextOffset.current : 0;
    const docs = await listMapWorkspaceDocuments('radio', signal, { offset, limit: 100 });
    const valid: SavedRadioStudy[] = [];
    let skipped = 0;
    for (const doc of docs) {
      try {
        valid.push({
          id: doc.id,
          title: doc.title,
          revision: doc.revision,
          teamId: doc.team_id,
          snapshot: parseRfStudy(doc.payload),
        });
      } catch {
        skipped++;
      }
    }
    if (signal.aborted) return;
    nextOffset.current = offset + docs.length;
    setHasMore(docs.length === 100);
    setItems((previous) =>
      append
        ? [...new Map([...previous, ...valid].map((item) => [item.id, item])).values()]
        : valid,
    );
    if (skipped) setMessage(`${skipped} saved studies use an unsupported or invalid format.`);
  };
  return {
    items,
    hasMore,
    loadMore: () => run((signal) => list(signal, true)),
    busy,
    message,
    refresh: () => run(list),
    save: (title: string, snapshot: RfStudySnapshot, existing?: SavedRadioStudy, teamId?: string) =>
      run(async (signal) => {
        const payload = parseRfStudy(snapshot) as unknown as Record<string, unknown>;
        if (existing)
          await updateMapWorkspaceDocument(
            existing.id,
            { title, payload, expected_revision: existing.revision },
            signal,
          );
        else
          await createMapWorkspaceDocument(
            { kind: 'radio', title, payload, ...(teamId ? { team_id: teamId } : {}) },
            signal,
          );
        if (!signal.aborted) await list(signal);
      }),
    remove: (id: string) =>
      run(async (signal) => {
        await removeMapWorkspaceDocument(id, signal);
        if (!signal.aborted) await list(signal);
      }),
  };
}
