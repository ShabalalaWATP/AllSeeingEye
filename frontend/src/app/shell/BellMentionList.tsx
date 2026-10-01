import { useCallback, useRef, useState } from 'react';
import { useNavigate } from 'react-router';

import { Button } from '@/components/ui/Button';
import { markMentionsRead, openMention } from '@/lib/api/bell';
import type { BellMention } from '@/lib/api/bell';
import { describeError, isApiError } from '@/lib/api/errors';
import { formatUtc } from '@/lib/format';
import { teamThreadPath } from '@/lib/teamBoardLinks';

import { headingClass } from './BellAlertList';
import type { NotificationBellState } from './useNotificationBell';

const openClass =
  'block w-full rounded-md px-2 py-2 text-left hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-ember disabled:opacity-60';
const GONE =
  'This mention is no longer available. The post may have been removed, or you may no longer be in that team.';

/**
 * Unread board mentions for this account. Snippets are plain text. Opening re-checks the
 * post against current membership before navigating, and marks only this account's notice
 * read; nobody else's mention changes.
 */
export function BellMentionList({
  state,
  keepFocus,
}: {
  state: NotificationBellState;
  /** Keeps focus in the bell if this section empties and unmounts. */
  keepFocus: () => void;
}) {
  const navigate = useNavigate();
  const { mentions, close, refresh, updateBell } = state;
  const [pending, setPending] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ postId: string | null; text: string } | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);

  const open = useCallback(
    async (mention: BellMention) => {
      if (pending !== null) return;
      setPending(mention.post_id);
      setNotice(null);
      try {
        const target = await openMention(mention.post_id);
        close();
        void navigate(teamThreadPath(target.team_id, target.thread_id));
      } catch (error) {
        const gone = isApiError(error) && error.status === 404;
        setNotice({
          postId: mention.post_id,
          text: gone ? GONE : `Could not open this mention. ${describeError(error)}`,
        });
        if (gone) void refresh();
      } finally {
        setPending(null);
      }
    },
    [close, navigate, pending, refresh],
  );

  const markShown = useCallback(async () => {
    if (pending !== null) return;
    const ids = mentions.items.map((item) => item.post_id);
    setPending('all');
    setNotice(null);
    try {
      const unread = await markMentionsRead(ids);
      updateBell((bell) => ({
        ...bell,
        mentions: {
          ...bell.mentions,
          items: bell.mentions.items.filter((item) => !ids.includes(item.post_id)),
          unread,
        },
      }));
      setNotice({ postId: null, text: 'Mentions marked as read.' });
      heading.current?.focus();
      keepFocus();
      void refresh();
    } catch (error) {
      setNotice({ postId: null, text: `Not marked as read. ${describeError(error)} Try again.` });
    } finally {
      setPending(null);
    }
  }, [keepFocus, mentions.items, pending, refresh, updateBell]);

  return (
    <section aria-labelledby="bell-mentions-heading">
      <h3 id="bell-mentions-heading" ref={heading} tabIndex={-1} className={headingClass}>
        Mentions
      </h3>
      {mentions.error ? (
        <p className="px-2 pt-1 text-sm text-muted">Mentions could not be loaded.</p>
      ) : (
        <ul className="mt-1" aria-label="Unread mentions">
          {mentions.items.map((mention) => (
            <li key={mention.post_id} aria-busy={pending === mention.post_id}>
              <button
                type="button"
                className={openClass}
                disabled={pending !== null}
                onClick={() => void open(mention)}
              >
                <span className="block text-sm text-text">
                  {mention.author_name} mentioned you in {mention.team_name}
                </span>
                <span className="mt-0.5 block text-xs break-words text-muted">
                  {mention.snippet}
                </span>
                <span className="mt-0.5 block text-xs text-muted">
                  {formatUtc(mention.created_at)}
                </span>
              </button>
              {notice?.postId === mention.post_id && (
                <p className="mx-2 mt-1 text-xs text-muted">{notice.text}</p>
              )}
            </li>
          ))}
        </ul>
      )}
      {mentions.total > mentions.items.length && (
        <p className="px-2 pt-1 text-xs text-muted">
          {mentions.total >= 100 ? '100 or more' : mentions.total} unread in total.
        </p>
      )}
      <p
        role="status"
        className={notice?.postId === null ? 'px-2 pt-1 text-xs text-muted' : 'sr-only'}
      >
        {notice?.postId === null ? notice.text : ''}
      </p>
      {mentions.items.length > 0 && (
        <Button
          variant="ghost"
          className="mx-1 min-h-11 text-xs"
          busy={pending === 'all'}
          busyLabel="Marking as read…"
          disabled={pending !== null && pending !== 'all'}
          onClick={() => void markShown()}
        >
          Mark shown mentions as read
        </Button>
      )}
    </section>
  );
}
