import { useCallback, useEffect, useMemo, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextAreaField } from '@/components/ui/Field';
import { asApiError, describeError } from '@/lib/api/errors';
import {
  createBoardPost,
  deleteBoardPost,
  editBoardPost,
  listBoardPosts,
  pinBoardPost,
  type TeamBoardPost as BoardPost,
} from '@/lib/api/teamBoard';

import type { TeamCapabilities } from './teamCapabilities';

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value),
  );
}

function BoardCard({
  post,
  canModerate,
  isAuthor,
  busy,
  onEdit,
  onDelete,
  onPin,
  onReply,
}: {
  post: BoardPost;
  canModerate: boolean;
  isAuthor: boolean;
  busy: boolean;
  onEdit: (post: BoardPost) => void;
  onDelete: (post: BoardPost) => void;
  onPin: (post: BoardPost) => void;
  onReply: (post: BoardPost) => void;
}) {
  const removed = post.deleted_at !== null;
  return (
    <article
      className={`border p-4 ${post.is_pinned ? 'border-amber/50 bg-amber/5' : 'border-line bg-surface/40'}`}
    >
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-text">
            {post.author_name}
            {post.is_pinned ? <span className="ml-2 text-xs text-amber">Pinned</span> : null}
          </p>
          <p className="mt-1 text-xs text-muted">{formatDate(post.updated_at)}</p>
        </div>
        {removed ? <span className="text-xs text-muted">Removed</span> : null}
      </header>
      <p
        className={`mt-3 whitespace-pre-wrap text-sm leading-6 ${removed ? 'text-muted' : 'text-text'}`}
      >
        {post.text}
      </p>
      {!removed ? (
        <div className="mt-4 flex flex-wrap gap-1">
          {isAuthor || canModerate ? (
            <Button variant="ghost" disabled={busy} onClick={() => onEdit(post)}>
              Edit
            </Button>
          ) : null}
          {isAuthor || canModerate ? (
            <Button variant="ghost" disabled={busy} onClick={() => onDelete(post)}>
              Remove
            </Button>
          ) : null}
          {canModerate && post.parent_id === null ? (
            <Button variant="ghost" disabled={busy} onClick={() => onPin(post)}>
              {post.is_pinned ? 'Unpin' : 'Pin'}
            </Button>
          ) : null}
          {post.parent_id === null ? (
            <Button variant="ghost" disabled={busy} onClick={() => onReply(post)}>
              Reply
            </Button>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}

export function TeamBoard({
  teamId,
  teamName,
  userId,
  capabilities,
}: {
  teamId: string;
  teamName: string;
  userId: string;
  capabilities: TeamCapabilities;
}) {
  const [posts, setPosts] = useState<BoardPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const [editing, setEditing] = useState<BoardPost | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await listBoardPosts(teamId);
      setPosts(page.items);
    } catch (caught) {
      setError(describeError(asApiError(caught)));
    } finally {
      setLoading(false);
    }
  }, [teamId]);

  useEffect(() => {
    // Load board state after the initial shell has rendered, then replace it
    // with the authorised response (or the access error) from the server.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  const roots = useMemo(() => posts.filter((post) => post.parent_id === null), [posts]);
  const replies = useMemo(() => {
    const grouped = new Map<string, BoardPost[]>();
    for (const post of posts) {
      if (post.parent_id === null) continue;
      const existing = grouped.get(post.parent_id) ?? [];
      existing.push(post);
      grouped.set(post.parent_id, existing);
    }
    return grouped;
  }, [posts]);

  async function save() {
    const text = draft.trim();
    if (!text || busy) return;
    setBusy(true);
    setError(null);
    try {
      const saved = editing
        ? await editBoardPost(teamId, editing.id, text, editing.revision)
        : await createBoardPost(teamId, text, replyTo ?? undefined);
      setPosts((current) => {
        const without = current.filter((post) => post.id !== saved.id);
        return [saved, ...without];
      });
      setDraft('');
      setReplyTo(null);
      setEditing(null);
    } catch (caught) {
      setError(describeError(asApiError(caught)));
    } finally {
      setBusy(false);
    }
  }

  async function remove(post: BoardPost) {
    if (busy) return;
    setBusy(true);
    try {
      await deleteBoardPost(teamId, post.id, post.revision);
      await load();
    } catch (caught) {
      setError(describeError(asApiError(caught)));
    } finally {
      setBusy(false);
    }
  }

  async function togglePin(post: BoardPost) {
    if (busy) return;
    setBusy(true);
    try {
      const updated = await pinBoardPost(teamId, post.id, !post.is_pinned, post.revision);
      setPosts((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (caught) {
      setError(describeError(asApiError(caught)));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex flex-col gap-6" aria-labelledby="team-board-heading">
      <div>
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-amber">
          Shared context
        </p>
        <h3 id="team-board-heading" className="mt-2 text-xl font-semibold">
          {teamName} board
        </h3>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Plain-text handovers and questions for active team members. Formal reports keep their own
          provenance.
        </p>
      </div>
      {error ? (
        <Alert tone="error">
          {error}{' '}
          <Button variant="ghost" onClick={() => void load()}>
            Retry
          </Button>
        </Alert>
      ) : null}
      {capabilities.isMember && capabilities.teamIsActive ? (
        <div className="border border-line bg-surface/50 p-4">
          <TextAreaField
            label={editing ? 'Edit post' : replyTo ? 'Reply' : 'New board post'}
            hint="Plain text only. Posts are limited to 4,000 characters and replies to 2,000."
            value={draft}
            maxLength={editing?.parent_id ? 2000 : replyTo ? 2000 : 4000}
            onChange={(event) => setDraft(event.target.value)}
            disabled={busy}
          />
          <div className="mt-3 flex flex-wrap gap-2">
            <Button disabled={busy || draft.trim() === ''} onClick={() => void save()}>
              {editing ? 'Save changes' : replyTo ? 'Post reply' : 'Post update'}
            </Button>
            {editing || replyTo ? (
              <Button
                variant="ghost"
                disabled={busy}
                onClick={() => {
                  setEditing(null);
                  setReplyTo(null);
                  setDraft('');
                }}
              >
                Cancel
              </Button>
            ) : null}
          </div>
        </div>
      ) : null}
      {loading ? <LoadingNote label="Loading team board" /> : null}
      {!loading && roots.length === 0 ? (
        <div className="border border-dashed border-line bg-surface/30 p-8 text-center">
          <h4 className="text-base font-semibold">No board updates yet</h4>
          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted">
            Share a short handover or question with the team.
          </p>
        </div>
      ) : null}
      <div className="flex flex-col gap-4">
        {roots.map((post) => (
          <div key={post.id} className="flex flex-col gap-2">
            <BoardCard
              post={post}
              canModerate={capabilities.canManageMembers}
              isAuthor={post.author_id === userId}
              busy={busy}
              onEdit={(value) => {
                setEditing(value);
                setReplyTo(null);
                setDraft(value.text);
              }}
              onDelete={(value) => void remove(value)}
              onPin={(value) => void togglePin(value)}
              onReply={(value) => {
                setReplyTo(value.id);
                setEditing(null);
                setDraft('');
              }}
            />
            {replies.get(post.id)?.map((reply) => (
              <div key={reply.id} className="ml-5 border-l-2 border-line pl-4">
                <BoardCard
                  post={reply}
                  canModerate={capabilities.canManageMembers}
                  isAuthor={reply.author_id === userId}
                  busy={busy}
                  onEdit={(value) => {
                    setEditing(value);
                    setReplyTo(null);
                    setDraft(value.text);
                  }}
                  onDelete={(value) => void remove(value)}
                  onPin={() => undefined}
                  onReply={() => undefined}
                />
              </div>
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}
