import { useMemo } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextAreaField } from '@/components/ui/Field';
import type { TeamBoardPost } from '@/lib/api/teamBoard';

import { BoardPostCard } from './BoardPostCard';
import type { TeamCapabilities } from './teamCapabilities';
import { useTeamBoard } from './useTeamBoard';

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
  const board = useTeamBoard(teamId);
  const canWrite = capabilities.teamIsActive && (capabilities.isMember || capabilities.isAdmin);
  const canModerate = capabilities.canManageMembers;

  const repliesByParent = useMemo(() => {
    const grouped = new Map<string, TeamBoardPost[]>();
    for (const reply of board.replies) {
      if (reply.parent_id === null) continue;
      grouped.set(reply.parent_id, [...(grouped.get(reply.parent_id) ?? []), reply]);
    }
    return grouped;
  }, [board.replies]);

  const card = (post: TeamBoardPost) => (
    <BoardPostCard
      post={post}
      userId={userId}
      canModerate={canModerate}
      canWrite={canWrite}
      busy={board.busy}
      onEdit={board.startEdit}
      onReply={board.startReply}
      onModerate={board.moderate}
    />
  );
  const replyMaximum = board.editing?.parent_id || board.replyTo ? 2000 : 4000;

  return (
    <section className="flex flex-col gap-6" aria-labelledby="team-board-heading">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-amber">
            Shared context
          </p>
          <h3 id="team-board-heading" className="mt-2 text-xl font-semibold">
            {teamName} board
          </h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
            Plain-text handovers and questions for active team members. Formal reports keep their
            own provenance.
          </p>
        </div>
        {board.unread > 0 ? (
          <span
            className="rounded-full border border-amber/50 bg-amber/10 px-3 py-1 text-xs font-medium text-amber"
            role="status"
          >
            {board.unread >= 100 ? '100+' : board.unread} new since your last visit
          </span>
        ) : null}
      </div>
      {/* The live region stays mounted so screen readers announce later updates. */}
      <p aria-live="polite" className={board.refreshNotice ? 'text-xs text-muted' : 'sr-only'}>
        {board.refreshNotice}
      </p>
      {board.accessLost ? (
        <Alert tone="warning" title="Team access changed">
          This board is no longer available to your account, so automatic refresh has stopped. Any
          unsent draft is kept in this tab. Refresh the team list to check your current workspaces.{' '}
          <Button variant="ghost" onClick={() => void board.load()}>
            Retry
          </Button>
        </Alert>
      ) : null}
      {board.error ? (
        <Alert tone="error">
          {board.error}{' '}
          <Button variant="ghost" onClick={() => void board.load()}>
            Retry
          </Button>
        </Alert>
      ) : null}
      {board.conflict ? (
        <Alert tone="warning" title="The board changed">
          {board.conflict} Your draft is kept. Reload to see the latest version, then save again.{' '}
          <Button variant="ghost" onClick={() => void board.reloadAfterConflict()}>
            Reload board
          </Button>
        </Alert>
      ) : null}
      {board.accessLost ? null : canWrite ? (
        <div className="border border-line bg-surface/50 p-4">
          <TextAreaField
            label={
              board.editing
                ? 'Edit post'
                : board.replyTo
                  ? `Reply to ${board.replyTo.author_name}`
                  : 'New board post'
            }
            hint="Plain text only. Posts are limited to 4,000 characters and replies to 2,000."
            value={board.draft}
            maxLength={replyMaximum}
            onChange={(event) => board.setDraft(event.target.value)}
            disabled={board.busy}
          />
          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              disabled={board.busy || board.draft.trim() === ''}
              onClick={() => void board.save()}
            >
              {board.editing ? 'Save changes' : board.replyTo ? 'Post reply' : 'Post update'}
            </Button>
            {board.editing || board.replyTo ? (
              <Button variant="ghost" disabled={board.busy} onClick={board.cancel}>
                Cancel
              </Button>
            ) : null}
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted">
          {capabilities.teamIsActive
            ? 'Only team members can post.'
            : 'This team is archived, so its board is read-only.'}
        </p>
      )}
      {board.loading && board.posts.length === 0 ? (
        <LoadingNote label="Loading team board" />
      ) : null}
      {!board.loading && !board.error && !board.accessLost && board.posts.length === 0 ? (
        <div className="border border-dashed border-line bg-surface/30 p-8 text-center">
          <h4 className="text-base font-semibold">No board updates yet</h4>
          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted">
            Share a short handover or question with the team.
          </p>
        </div>
      ) : null}
      <div className="flex flex-col gap-4">
        {board.posts.map((post) => (
          <div key={post.id} className="flex flex-col gap-2">
            {card(post)}
            {repliesByParent.get(post.id)?.map((reply) => (
              <div key={reply.id} className="ml-5 border-l-2 border-line pl-4">
                {card(reply)}
              </div>
            ))}
          </div>
        ))}
      </div>
      {board.nextOffset !== null ? (
        <Button variant="secondary" disabled={board.busy} onClick={() => void board.loadMore()}>
          Load older posts
        </Button>
      ) : null}
    </section>
  );
}
