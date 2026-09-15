import { useCallback, useEffect, useRef, useState } from 'react';

import { asApiError, describeError } from '@/lib/api/errors';
import {
  createBoardPost,
  editBoardPost,
  listBoardPosts,
  markBoardRead,
  pinBoardPost,
  removeBoardPost,
  type TeamBoardPost,
} from '@/lib/api/teamBoard';
import { useVisiblePolling, type PollOutcome } from '@/lib/hooks/useVisiblePolling';

import { appendPage, countNewPosts, mergeFirstPage, newestPost } from './boardMerge';
import { isTeamAccessLoss as isAccessLoss } from './teamCapabilities';

export type BoardAction = 'remove' | 'pin';

export const BOARD_REFRESH_INTERVAL = 30_000;

function notifyNew(count: number): string | null {
  if (count === 0) return null;
  return count === 1 ? '1 new post added' : `${count} new posts added`;
}

/**
 * Board state, including a draft that survives refreshes and revision conflicts.
 * The server remains the authority for every permission and revision check.
 */
export function useTeamBoard(teamId: string) {
  const [posts, setPosts] = useState<TeamBoardPost[]>([]);
  const [replies, setReplies] = useState<TeamBoardPost[]>([]);
  const [nextOffset, setNextOffset] = useState<number | null>(null);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<string | null>(null);
  const [accessLost, setAccessLost] = useState(false);
  const [refreshNotice, setRefreshNotice] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [replyTo, setReplyTo] = useState<TeamBoardPost | null>(null);
  const [editing, setEditing] = useState<TeamBoardPost | null>(null);
  const editingRef = useRef<TeamBoardPost | null>(null);
  const shown = useRef<TeamBoardPost[]>([]);
  const olderLoaded = useRef(false);
  const activeRequests = useRef(0);
  useEffect(() => {
    editingRef.current = editing;
  }, [editing]);
  useEffect(() => {
    shown.current = [...posts, ...replies];
  }, [posts, replies]);

  // Stop showing content the account can no longer see; drafts stay local to this tab.
  const loseAccess = useCallback(() => {
    setAccessLost(true);
    setPosts([]);
    setReplies([]);
    setNextOffset(null);
    setUnread(0);
    setRefreshNotice(null);
  }, []);

  const refresh = useCallback(
    async (signal: AbortSignal): Promise<PollOutcome> => {
      // Explicit loads and writes take priority; a manual load also aborts this request.
      if (activeRequests.current > 0) return 'skipped';
      try {
        const page = await listBoardPosts(teamId, 0, 20, signal);
        const incoming = [...page.items, ...page.replies];
        const added = countNewPosts(shown.current, incoming);
        setPosts((current) => mergeFirstPage(current, page.items));
        setReplies((current) => mergeFirstPage(current, page.replies));
        if (!olderLoaded.current) setNextOffset(page.next_offset);
        setUnread(page.unread_count);
        setRefreshNotice(notifyNew(added));
        const latest = newestPost(incoming);
        if (latest && added > 0 && page.unread_count > 0 && document.visibilityState !== 'hidden') {
          void markBoardRead(teamId, latest.id).catch(() => undefined);
        }
        return 'ok';
      } catch (caught) {
        if (signal.aborted) return 'skipped';
        const failure = asApiError(caught);
        if (!isAccessLoss(failure.status)) {
          setRefreshNotice('Automatic refresh failed. The board will try again shortly.');
          return 'failed';
        }
        loseAccess();
        return 'stop';
      }
    },
    [loseAccess, teamId],
  );
  const { markLoaded } = useVisiblePolling({
    enabled: !accessLost && !loading,
    intervalMs: BOARD_REFRESH_INTERVAL,
    poll: refresh,
  });

  const load = useCallback(async () => {
    activeRequests.current += 1;
    setLoading(true);
    setError(null);
    try {
      const page = await listBoardPosts(teamId);
      olderLoaded.current = false;
      setAccessLost(false);
      setRefreshNotice(null);
      setPosts(page.items);
      setReplies(page.replies);
      setNextOffset(page.next_offset);
      setUnread(page.unread_count);
      const current = editingRef.current;
      if (current) {
        // Keep the draft, but move the edit onto the latest revision the user has now seen.
        const fresh = [...page.items, ...page.replies].find((post) => post.id === current.id);
        setEditing(fresh?.deleted_at === null ? fresh : null);
      }
      const latest = newestPost([...page.items, ...page.replies]);
      if (latest && page.unread_count > 0 && document.visibilityState !== 'hidden') {
        void markBoardRead(teamId, latest.id).catch(() => undefined);
      }
    } catch (caught) {
      const failure = asApiError(caught);
      if (isAccessLoss(failure.status)) loseAccess();
      else setError(describeError(failure));
    } finally {
      // A failed load also counts as a recent attempt, so polling does not retry at once.
      markLoaded();
      activeRequests.current -= 1;
      setLoading(false);
    }
  }, [loseAccess, markLoaded, teamId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  const loadMore = useCallback(async () => {
    if (nextOffset === null || busy) return;
    setBusy(true);
    activeRequests.current += 1;
    try {
      const page = await listBoardPosts(teamId, nextOffset);
      olderLoaded.current = true;
      setPosts((current) => appendPage(current, page.items));
      setReplies((current) => appendPage(current, page.replies));
      setNextOffset(page.next_offset);
    } catch (caught) {
      setError(describeError(asApiError(caught)));
    } finally {
      activeRequests.current -= 1;
      setBusy(false);
    }
  }, [busy, nextOffset, teamId]);

  function handleFailure(caught: unknown) {
    const failure = asApiError(caught);
    if (failure.status === 409) setConflict(failure.message);
    else setError(describeError(failure));
  }

  async function save() {
    const text = draft.trim();
    if (!text || busy) return;
    setBusy(true);
    setError(null);
    activeRequests.current += 1;
    try {
      if (editing) await editBoardPost(teamId, editing.id, text, editing.revision);
      else await createBoardPost(teamId, text, replyTo?.id);
      setConflict(null);
      setDraft('');
      setReplyTo(null);
      setEditing(null);
      await load();
    } catch (caught) {
      handleFailure(caught);
    } finally {
      activeRequests.current -= 1;
      setBusy(false);
    }
  }

  async function moderate(post: TeamBoardPost, action: BoardAction, reason?: string) {
    if (busy) return false;
    setBusy(true);
    setError(null);
    activeRequests.current += 1;
    try {
      if (action === 'remove') await removeBoardPost(teamId, post.id, post.revision, reason);
      else await pinBoardPost(teamId, post.id, !post.is_pinned, post.revision, reason);
      await load();
      return true;
    } catch (caught) {
      handleFailure(caught);
      return false;
    } finally {
      activeRequests.current -= 1;
      setBusy(false);
    }
  }

  async function reloadAfterConflict() {
    setConflict(null);
    await load();
  }

  function startEdit(post: TeamBoardPost) {
    setEditing(post);
    setReplyTo(null);
    setDraft(post.text);
  }

  function startReply(post: TeamBoardPost) {
    setReplyTo(post);
    setEditing(null);
  }

  function cancel() {
    setEditing(null);
    setReplyTo(null);
    setDraft('');
    setConflict(null);
  }

  return {
    posts,
    replies,
    nextOffset,
    unread,
    loading,
    busy,
    error,
    conflict,
    accessLost,
    refreshNotice,
    draft,
    replyTo,
    editing,
    setDraft,
    load,
    loadMore,
    save,
    moderate,
    reloadAfterConflict,
    startEdit,
    startReply,
    cancel,
  };
}
