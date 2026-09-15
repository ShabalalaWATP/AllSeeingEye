import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import type { TeamBoardPost } from '@/lib/api/teamBoard';

import type { BoardAction } from './useTeamBoard';

const REASON_MIN = 3;
const REASON_MAX = 300;

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value),
  );
}

function actionLabel(post: TeamBoardPost, action: BoardAction): string {
  if (action === 'remove') return 'Remove post';
  return post.is_pinned ? 'Unpin post' : 'Pin post';
}

/** Confirms an action; someone else's post also needs a reason recorded only in the audit log. */
function ConfirmAction({
  post,
  action,
  needsReason,
  busy,
  onConfirm,
  onCancel,
}: {
  post: TeamBoardPost;
  action: BoardAction;
  needsReason: boolean;
  busy: boolean;
  onConfirm: (reason?: string) => void;
  onCancel: () => void;
}) {
  const [reason, setReason] = useState('');
  const trimmed = reason.trim();
  const valid = !needsReason || (trimmed.length >= REASON_MIN && trimmed.length <= REASON_MAX);
  return (
    <div
      className="mt-4 border-t border-line/70 pt-3"
      role="group"
      aria-label={actionLabel(post, action)}
    >
      {needsReason ? (
        <TextField
          label="Moderation reason"
          hint="Required. Recorded in the audit log and not shown to the team."
          value={reason}
          maxLength={REASON_MAX}
          onChange={(event) => setReason(event.target.value)}
          disabled={busy}
        />
      ) : (
        <p className="text-sm text-muted">Remove your post? A tombstone stays in the thread.</p>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        <Button
          variant={action === 'remove' ? 'danger' : 'secondary'}
          disabled={busy || !valid}
          onClick={() => onConfirm(needsReason ? trimmed : undefined)}
        >
          Confirm {actionLabel(post, action).toLowerCase()}
        </Button>
        <Button variant="ghost" disabled={busy} onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </div>
  );
}

export function BoardPostCard({
  post,
  userId,
  canModerate,
  canWrite,
  busy,
  onEdit,
  onReply,
  onModerate,
}: {
  post: TeamBoardPost;
  userId: string;
  canModerate: boolean;
  canWrite: boolean;
  busy: boolean;
  onEdit: (post: TeamBoardPost) => void;
  onReply: (post: TeamBoardPost) => void;
  onModerate: (post: TeamBoardPost, action: BoardAction, reason?: string) => Promise<boolean>;
}) {
  const [pending, setPending] = useState<BoardAction | null>(null);
  const removed = post.deleted_at !== null;
  const isAuthor = post.author_id === userId;
  const canRemove = canWrite && (isAuthor || canModerate);
  const canPin = canWrite && canModerate && post.parent_id === null;

  return (
    <article
      aria-label={`Post by ${post.author_name}`}
      className={`border p-4 ${post.is_pinned ? 'border-amber/50 bg-amber/5' : 'border-line bg-surface/40'}`}
    >
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-text">
            {post.author_name}
            {post.is_pinned ? <span className="ml-2 text-xs text-amber">Pinned</span> : null}
          </p>
          <p className="mt-1 text-xs text-muted">
            {formatDate(post.created_at)}
            {post.edited_at && !removed ? ` · Edited ${formatDate(post.edited_at)}` : null}
          </p>
        </div>
        {removed ? (
          <span className="text-xs text-muted">
            {post.removal === 'moderator' ? 'Removed by a moderator' : 'Removed by author'}
          </span>
        ) : null}
      </header>
      {/* Plain text only: rendered as a React text node, never as HTML. */}
      <p
        className={`mt-3 whitespace-pre-wrap break-words text-sm leading-6 ${removed ? 'text-muted' : 'text-text'}`}
      >
        {post.text}
      </p>
      {!removed && pending === null ? (
        <div className="mt-4 flex flex-wrap gap-1">
          {canWrite && isAuthor ? (
            <Button variant="ghost" disabled={busy} onClick={() => onEdit(post)}>
              Edit
            </Button>
          ) : null}
          {canRemove ? (
            <Button variant="ghost" disabled={busy} onClick={() => setPending('remove')}>
              Remove
            </Button>
          ) : null}
          {canPin ? (
            <Button variant="ghost" disabled={busy} onClick={() => setPending('pin')}>
              {post.is_pinned ? 'Unpin' : 'Pin'}
            </Button>
          ) : null}
          {canWrite && post.parent_id === null ? (
            <Button variant="ghost" disabled={busy} onClick={() => onReply(post)}>
              Reply
            </Button>
          ) : null}
        </div>
      ) : null}
      {!removed && pending !== null ? (
        <ConfirmAction
          post={post}
          action={pending}
          needsReason={!isAuthor}
          busy={busy}
          onCancel={() => setPending(null)}
          onConfirm={(reason) => {
            void onModerate(post, pending, reason).then((done) => {
              if (done) setPending(null);
            });
          }}
        />
      ) : null}
    </article>
  );
}
