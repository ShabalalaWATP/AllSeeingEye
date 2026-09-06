/**
 * Loads the current events once and keeps them current over the stream for as
 * long as the globe is mounted. The stream borrows the session's access token and
 * asks the auth store for a fresh one when the server closes the stream.
 */
import { useEffect } from 'react';

import { EventStreamClient } from '@/lib/sse';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { useEventsStore } from '@/stores/events';

export const STREAM_URL = '/api/stream';

export function useLiveEvents(enabled = true): void {
  useEffect(() => {
    if (!enabled) return;
    const events = useEventsStore.getState();
    void events.load();
    const client = new EventStreamClient({
      url: STREAM_URL,
      getToken: async (refresh) => {
        const auth = useAuthStore.getState();
        if (refresh || auth.accessToken === null) return auth.refresh();
        return auth.accessToken;
      },
      onMessage: (message) => {
        if (message.event === 'access.changed') invalidateWorkspaceAccess();
        useEventsStore.getState().handleStreamMessage(message);
      },
      onStatus: (status) => {
        useEventsStore.getState().setStatus(status);
      },
    });
    client.start();
    return () => {
      client.stop();
    };
  }, [enabled]);
}
