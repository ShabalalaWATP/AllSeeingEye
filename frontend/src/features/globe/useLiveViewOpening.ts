/**
 * Opens a live view explicitly: from the saved-views panel or from a `/?view=<id>` link.
 * Only the view ID travels in a link; every open re-reads the document under the viewer's
 * current access. Nothing opens automatically at sign-in.
 */
import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router';

import { getLiveView } from '@/lib/api/liveViews';
import { subscribeWorkspaceAccess } from '@/lib/workspaceAccess';
import type { LiveViewControls } from './useLiveViewControls';

export interface LiveViewNoticeState {
  status: 'loading' | 'opened' | 'unavailable';
  title: string | null;
  dropped: readonly string[];
}

export const VIEW_PARAM = 'view';
const LOADING: LiveViewNoticeState = { status: 'loading', title: null, dropped: [] };

export function useLiveViewOpening(controls: LiveViewControls) {
  const [params, setParams] = useSearchParams();
  const linked = params.get(VIEW_PARAM);
  const { apply } = controls;
  // Each open is its own object, so reopening the same view starts a fresh read.
  const [pending, setPending] = useState<{ id: string } | null>(null);
  const [outcome, setOutcome] = useState<{
    request: { id: string };
    notice: LiveViewNoticeState;
  } | null>(null);
  const [seenLink, setSeenLink] = useState<string | null>(null);
  if (linked !== seenLink) {
    setSeenLink(linked);
    if (linked) setPending({ id: linked });
  }
  // Take the ID out of the address at once; the read keeps its own copy.
  useEffect(() => {
    if (!linked) return;
    setParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        next.delete(VIEW_PARAM);
        return next;
      },
      { replace: true },
    );
  }, [linked, setParams]);
  useEffect(() => {
    if (!pending) return;
    const controller = new AbortController();
    getLiveView(pending.id, controller.signal).then(
      (result) => {
        if (controller.signal.aborted) return;
        apply(result.view);
        setOutcome({
          request: pending,
          notice: { status: 'opened', title: result.document.title, dropped: result.dropped },
        });
      },
      () => {
        if (!controller.signal.aborted)
          setOutcome({
            request: pending,
            notice: { status: 'unavailable', title: null, dropped: [] },
          });
      },
    );
    return () => controller.abort();
  }, [pending, apply]);
  useEffect(() => subscribeWorkspaceAccess(() => setPending(null)), []);

  return {
    notice: pending === null ? null : outcome?.request === pending ? outcome.notice : LOADING,
    dismiss: () => setPending(null),
    /** Re-read a saved view under current access, exactly as a link does. */
    openId: (id: string) => setPending({ id }),
  };
}
