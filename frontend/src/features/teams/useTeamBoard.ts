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

export type BoardAction = 'remove' | 'pin';

function newest(posts: readonly TeamBoardPost[]): TeamBoardPost | undefined {
  return posts.reduce<TeamBoardPost | undefined>(
    (latest, post) => (latest === undefined || post.created_at > latest.created_at ? post : latest),
    undefined,
  );
}

function merge(current: TeamBoardPost[], incoming: readonly TeamBoardPost[]): TeamBoardPost[] {
  const known = new Set(incoming.map((post) => post.id));
  return [...current.filter((post) => !known.has(post.id)), ...incoming];
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
  const [draft, setDraft] = useState('');
  const [replyTo, setReplyTo] = useState<TeamBoardPost | null>(null);
  const [editing, setEditing] = useState<TeamBoardPost | null>(null);
  const editingRef = useRef<TeamBoardPost | null>(null);
  useEffect(() => {
    editingRef.current = editing;
  }, [editing]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await listBoardPosts(teamId);
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
      const latest = newest([...page.items, ...page.replies]);
      if (latest && page.unread_count > 0) {
        void markBoardRead(teamId, latest.id).catch(() => undefined);
      }
    } catch (caught) {
      setError(describeError(asApiError(caught)));
    } finally {
      setLoading(false);
    }
  }, [teamId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  const loadMore = useCallback(async () => {
    if (nextOffset === null || busy) return;
    setBusy(true);
    try {
      const page = await listBoardPosts(teamId, nextOffset);
      setPosts((current) => merge(current, page.items));
      setReplies((current) => merge(current, page.replies));
      setNextOffset(page.next_offset);
    } catch (caught) {
      setError(describeError(asApiError(caught)));
    } finally {
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
      setBusy(false);
    }
  }

  async function moderate(post: TeamBoardPost, action: BoardAction, reason?: string) {
    if (busy) return false;
    setBusy(true);
    setError(null);
    try {
      if (action === 'remove') await removeBoardPost(teamId, post.id, post.revision, reason);
      else await pinBoardPost(teamId, post.id, !post.is_pinned, post.revision, reason);
      await load();
      return true;
    } catch (caught) {
      handleFailure(caught);
      return false;
    } finally {
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
