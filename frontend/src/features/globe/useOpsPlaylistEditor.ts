/** Edit an ops-room playlist of saved views and saved areas that share its scope. */
import { useCallback, useEffect, useRef, useState } from 'react';

import { fetchAois } from '@/lib/api/direction';
import { describeError, isApiError } from '@/lib/api/errors';
import {
  getPlaylist,
  listLiveViews,
  listPlaylists,
  removeLiveDocument,
  savePlaylist,
} from '@/lib/api/liveViews';
import type { MapWorkspaceDocument } from '@/lib/api/mapWorkspace';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import {
  clampDwell,
  DEFAULT_DWELL_SECONDS,
  MAX_PLAYLIST_ENTRIES,
  type PlaylistEntry,
} from '@/lib/liveViews/opsPlaylist';
import { subscribeWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

export interface PlaylistSource {
  kind: PlaylistEntry['kind'];
  id: string;
  label: string;
  team_id: string | null;
  created_by: string;
}

async function loadSources() {
  const [playlists, views, areas] = await Promise.all([
    listPlaylists(),
    listLiveViews(),
    fetchAois(),
  ]);
  const sources: PlaylistSource[] = [
    ...views.map((view) => ({ ...view, kind: 'view' as const, label: `View: ${view.title}` })),
    ...areas.map((area) => ({ ...area, kind: 'area' as const, label: `Area: ${area.name}` })),
  ];
  return { playlists, sources };
}

export function useOpsPlaylistEditor() {
  const resource = useScopedResource(loadSources);
  const actor = useAuthStore((state) => state.user?.id ?? null);
  const [active, setActive] = useState<MapWorkspaceDocument | null>(null);
  const [title, setTitle] = useState('Wall rotation');
  const [entries, setEntries] = useState<PlaylistEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const request = useRef<AbortController | null>(null);

  const clear = useCallback(() => {
    request.current?.abort();
    setActive(null);
    setTitle('Wall rotation');
    setEntries([]);
    setError(null);
    setNotice(null);
    setBusy(false);
  }, []);
  useEffect(() => subscribeWorkspaceAccess(clear), [clear]);

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
      if (controller.signal.aborted) return;
      setError(
        isApiError(caught) && caught.status === 409
          ? 'This playlist changed elsewhere or access changed. Open it again before saving.'
          : describeError(caught),
      );
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  };

  /** Linked records must share the playlist's personal owner or team. */
  const compatible = (teamId: string | null) =>
    (resource.data?.sources ?? []).filter((source) =>
      teamId ? source.team_id === teamId : source.team_id === null && source.created_by === actor,
    );

  return {
    loading: resource.loading,
    loadError: resource.error ? describeError(resource.error) : null,
    playlists: resource.data?.playlists ?? [],
    sources: resource.data?.sources ?? [],
    compatible,
    active,
    title,
    setTitle,
    entries,
    busy,
    error,
    notice,
    reload: () => void resource.reload(),
    startNew: clear,
    open: (id: string) =>
      run(async (signal) => {
        const result = await getPlaylist(id, signal);
        if (signal.aborted) return;
        setActive(result.document);
        setTitle(result.document.title);
        setEntries(result.playlist.entries);
      }),
    add: (source: PlaylistSource) =>
      setEntries((previous) =>
        previous.length >= MAX_PLAYLIST_ENTRIES
          ? previous
          : [
              ...previous,
              {
                kind: source.kind,
                id: source.id,
                caption: '',
                dwell_seconds: DEFAULT_DWELL_SECONDS,
              },
            ],
      ),
    update: (index: number, patch: Partial<Pick<PlaylistEntry, 'caption' | 'dwell_seconds'>>) =>
      setEntries((previous) =>
        previous.map((entry, position) =>
          position === index
            ? {
                ...entry,
                ...patch,
                ...(patch.dwell_seconds === undefined
                  ? {}
                  : { dwell_seconds: clampDwell(patch.dwell_seconds) }),
              }
            : entry,
        ),
      ),
    move: (index: number, offset: -1 | 1) =>
      setEntries((previous) => {
        const target = index + offset;
        if (target < 0 || target >= previous.length) return previous;
        const next = [...previous];
        const [moved] = next.splice(index, 1);
        if (moved) next.splice(target, 0, moved);
        return next;
      }),
    remove: (index: number) =>
      setEntries((previous) => previous.filter((_, position) => position !== index)),
    save: (teamId?: string) =>
      run(async (signal) => {
        const saved = await savePlaylist(
          { version: 1, entries },
          title.trim(),
          { existing: active, ...(teamId ? { teamId } : {}) },
          signal,
        );
        if (signal.aborted) return;
        setActive(saved);
        setNotice(`Saved ${saved.title} (revision ${saved.revision}).`);
        void resource.refresh();
      }),
    destroy: () =>
      run(async (signal) => {
        if (!active) return;
        await removeLiveDocument(active.id, signal);
        if (signal.aborted) return;
        const name = active.title;
        clear();
        setNotice(`Deleted ${name}.`);
        void resource.refresh();
      }),
  };
}

export type OpsPlaylistEditor = ReturnType<typeof useOpsPlaylistEditor>;
