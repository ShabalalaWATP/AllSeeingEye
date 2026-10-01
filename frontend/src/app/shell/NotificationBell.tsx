import { useCallback, useEffect, useId, useRef, useState } from 'react';
import type { RefObject } from 'react';

import { useAuthStore } from '@/stores/auth';

import { NotificationPanel } from './NotificationPanel';
import { useBellAlertActions } from './useBellAlertActions';
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
  const hintId = useId();
  const wrapper = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const alertsHeading = useRef<HTMLHeadingElement>(null);
  const [settingsChosen, setSettings] = useState(false);
  const { open, unread, close, windowDays } = state;
  // When an acknowledged or muted item leaves the list, keep focus inside the bell.
  const keepFocus = useCallback(() => {
    setTimeout(() => {
      const active = document.activeElement;
      if (active !== null && active !== document.body && panel.current?.contains(active)) return;
      (alertsHeading.current ?? panel.current)?.focus();
    }, 0);
  }, []);
  const actions = useBellAlertActions(state, keepFocus);
  // The confirmation is a modal outside the popover; it must not dismiss the bell.
  useDismiss(open && actions.acknowledgeShown.target === null, close, wrapper, button);
  useEffect(() => {
    if (open) panel.current?.focus();
  }, [open]);
  const settings = open && settingsChosen;
  const toggleBell = () => {
    // Each opening starts on the notifications themselves.
    setSettings(false);
    state.toggle();
  };

  return (
    <div ref={wrapper} className="relative">
      <button
        ref={button}
        type="button"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        aria-label={describe(state)}
        aria-describedby={hintId}
        title="Notifications"
        onClick={toggleBell}
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
      <span id={hintId} hidden>
        Counts unacknowledged alerts from the last {windowDays} days and research finished since you
        last opened notifications.
      </span>
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
          <div className="flex items-center justify-between gap-2 px-2 pt-1 pb-3">
            <h2 className="text-sm font-semibold">Notifications</h2>
            <button
              type="button"
              aria-pressed={settings}
              onClick={() => setSettings((value) => !value)}
              className="min-h-11 rounded-md px-2 text-xs text-ember hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-ember"
            >
              {settings ? 'Back to notifications' : 'Settings'}
            </button>
          </div>
          <NotificationPanel
            state={state}
            actions={actions}
            settings={settings}
            headingRef={alertsHeading}
            returnFocus={panel}
          />
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
