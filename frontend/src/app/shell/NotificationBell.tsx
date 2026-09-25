import { useEffect, useId, useRef } from 'react';
import type { RefObject } from 'react';

import { useAuthStore } from '@/stores/auth';

import { NotificationPanel } from './NotificationPanel';
import { useNotificationBell } from './useNotificationBell';
import type { NotificationBellState } from './useNotificationBell';

const buttonClass =
  'relative inline-flex min-h-11 min-w-11 items-center justify-center rounded-md px-2 text-muted hover:bg-surface-2 hover:text-text focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember aria-expanded:bg-surface-2 aria-expanded:text-text';

function describe({ unread, loading, alerts, jobs }: NotificationBellState): string {
  if (unread > 0) return `Notifications, ${unread} unread`;
  if (loading) return 'Notifications';
  return alerts.error || jobs.error
    ? 'Notifications, could not be checked'
    : 'Notifications, nothing unread';
}

/** Escape, a click elsewhere or focus moving elsewhere closes the panel. */
function useDismiss(
  open: boolean,
  close: () => void,
  wrapper: RefObject<HTMLDivElement | null>,
  button: RefObject<HTMLButtonElement | null>,
) {
  useEffect(() => {
    if (!open) return;
    const outside = (target: EventTarget | null) =>
      !(target instanceof Node) || !wrapper.current?.contains(target);
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      close();
      button.current?.focus();
    };
    const onPointerDown = (event: PointerEvent) => {
      if (outside(event.target)) close();
    };
    const onFocusOut = (event: FocusEvent) => {
      if (event.relatedTarget !== null && outside(event.relatedTarget)) close();
    };
    const node = wrapper.current;
    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('pointerdown', onPointerDown);
    node?.addEventListener('focusout', onFocusOut);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.removeEventListener('pointerdown', onPointerDown);
      node?.removeEventListener('focusout', onFocusOut);
    };
  }, [open, close, wrapper, button]);
}

function BellControl({ userId }: { userId: string }) {
  const state = useNotificationBell(userId);
  const panelId = useId();
  const wrapper = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const { open, unread, close } = state;
  useDismiss(open, close, wrapper, button);
  useEffect(() => {
    if (open) panel.current?.focus();
  }, [open]);

  return (
    <div ref={wrapper} className="relative">
      <button
        ref={button}
        type="button"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        aria-label={describe(state)}
        title="Notifications"
        onClick={state.toggle}
        className={buttonClass}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
          <path d="M10.3 21a1.9 1.9 0 0 0 3.4 0" />
        </svg>
        {unread > 0 && (
          <span
            aria-hidden="true"
            className="absolute top-1 right-0.5 min-w-4.5 rounded-full bg-critical px-1 text-center font-mono text-xs leading-4.5 font-semibold text-ground"
          >
            {unread}
          </span>
        )}
      </button>
      <span role="status" className="sr-only">
        {unread > 0 ? `${unread} unread notifications` : ''}
      </span>
      {open && (
        <div
          ref={panel}
          id={panelId}
          role="dialog"
          aria-label="Notifications"
          tabIndex={-1}
          className="absolute top-full right-0 z-40 mt-2 max-h-[70vh] w-80 max-w-[calc(100vw-1rem)] overflow-y-auto rounded-lg border border-line bg-ground p-2 text-text shadow-card focus:outline-none"
        >
          <h2 className="px-2 pt-1 pb-3 text-sm font-semibold">Notifications</h2>
          <NotificationPanel state={state} />
        </div>
      )}
    </div>
  );
}

/** The top-bar bell. Nothing is requested until someone is signed in. */
export function NotificationBell() {
  const userId = useAuthStore((state) =>
    state.status === 'authenticated' && state.user?.is_active ? state.user.id : null,
  );
  // Keyed by account so the last-seen time and open state never cross users.
  return userId === null ? null : <BellControl key={userId} userId={userId} />;
}
