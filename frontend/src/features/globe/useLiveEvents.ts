/**
 * Loads the current events once and keeps them current over the stream for as
 * long as the globe is mounted. The stream borrows the session's access token and
 * asks the auth store for a fresh one when the server closes the stream.
 */
import { useEffect } from 'react';
import { usePageVisible } from '@/components/brand/useMotionPreferences';

import { streamHelloSchema } from '@/lib/api/eventSchemas';
import { EventStreamClient, type SseMessage } from '@/lib/sse';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { useEventsStore } from '@/stores/events';
import { EventUpdateBatch } from '@/stores/events.stream';

export const STREAM_URL = '/api/stream';

/** True only when the server confirms it replayed everything this mirror missed. */
function resumed(message: SseMessage): boolean {
  try {
    const parsed = streamHelloSchema.safeParse(JSON.parse(message.data) as unknown);
    return parsed.success && parsed.data.resumed === true;
  } catch {
    return false;
  }
}

export function useLiveEvents(enabled = true): void {
  const visible = usePageVisible();
  useEffect(() => {
    if (!enabled || !visible) return;
    const batch = new EventUpdateBatch(useEventsStore.getState);
    const releaseBarrier = useEventsStore.getState().onSnapshotStart(() => batch.flush());
    let fallback: ReturnType<typeof setTimeout> | null = null;
    // The id of a hello that has just started a snapshot, until the next frame.
    let reloadedAt: string | null = null;
    const onHello = (message: SseMessage) => {
      if (fallback !== null) clearTimeout(fallback);
      fallback = null;
      const events = useEventsStore.getState();
      const healthy = events.error === null && (events.loaded || events.loading);
      if (resumed(message) && healthy) return;
      // Take a snapshot after the subscription opens: first connection, a stream the
      // server could not resume, or a mirror that never finished loading.
      reloadedAt = message.id;
      void events.load();
    };
    const client = new EventStreamClient({
      url: STREAM_URL,
      getToken: async (refresh) => {
        const auth = useAuthStore.getState();
        if (refresh || auth.accessToken === null) return auth.refresh();
        return auth.accessToken;
      },
      onMessage: (message) => {
        if (message.event === 'hello') {
          onHello(message);
          return;
        }
        const duplicate =
          message.event === 'event.resync' && reloadedAt !== null && message.id === reloadedAt;
        reloadedAt = null;
        // An unresumable id is followed by a resync at the hello's own position. The
        // snapshot that hello started is already newer, so a second load is wasted.
        if (duplicate) return;
        if (message.event === 'access.changed') invalidateWorkspaceAccess();
        batch.receive(message);
      },
      onStatus: (status) => {
        useEventsStore.getState().setStatus(status);
      },
    });
    // Keep offline snapshots usable if subscription setup cannot finish.
    fallback = setTimeout(() => {
      fallback = null;
      void useEventsStore.getState().load();
    }, 3_000);
    client.start();
    return () => {
      if (fallback !== null) clearTimeout(fallback);
      client.stop();
      releaseBarrier();
      batch.clear();
      useEventsStore.getState().cancelLoad();
    };
  }, [enabled, visible]);
}
