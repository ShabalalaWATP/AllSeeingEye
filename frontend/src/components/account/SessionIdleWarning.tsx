import { useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { idleRemaining, showIdleWarning } from '@/lib/sessionActivity';
import { useAuthStore } from '@/stores/auth';

export function SessionIdleWarning({ now }: { now: number }) {
  const activity = useAuthStore((state) => state.activity);
  const checkingIdle = useAuthStore(
    (state) => state.pendingIdleCheck !== null || state.idleCheckRetryAt > 0,
  );
  return activity !== null && (checkingIdle || showIdleWarning(activity, now)) ? (
    <IdleWarning now={now} />
  ) : null;
}

function IdleWarning({ now }: { now: number }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const stay = useRef<HTMLButtonElement>(null);
  const title = useId();
  const description = useId();
  const activity = useAuthStore((state) => state.activity);
  const busy = useAuthStore(
    (state) => state.pendingActivity !== null || state.pendingIdleCheck !== null,
  );
  const checkingIdle = useAuthStore(
    (state) => state.pendingIdleCheck !== null || state.idleCheckRetryAt > 0,
  );
  const error = useAuthStore((state) => state.activityError);
  const retryAt = useAuthStore((state) => Math.max(state.activityRetryAt, state.idleCheckRetryAt));
  const minutes =
    activity === null ? 0 : Math.max(1, Math.ceil(idleRemaining(activity, now) / 60_000));
  const waiting = now < retryAt;

  useEffect(() => {
    const opener = document.activeElement;
    const element = dialog.current;
    const stopKeys = (event: KeyboardEvent) => event.stopPropagation();
    element?.addEventListener('keydown', stopKeys);
    element?.showModal();
    stay.current?.focus();
    return () => {
      element?.close();
      element?.removeEventListener('keydown', stopKeys);
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, []);

  return createPortal(
    <dialog
      ref={dialog}
      role="alertdialog"
      data-session-idle-warning="true"
      aria-modal="true"
      aria-labelledby={title}
      aria-describedby={description}
      className="m-auto w-[min(32rem,calc(100vw-2rem))] rounded-card border border-line bg-surface p-5 text-text shadow-card backdrop:bg-black/65"
      onCancel={(event) => event.preventDefault()}
    >
      <h2 id={title} className="text-lg font-semibold">
        You'll be signed out soon for security
      </h2>
      <div id={description} className="mt-3 space-y-2 text-sm leading-6 text-muted">
        <p role="status" aria-label="Session time remaining" aria-live="polite" aria-atomic="true">
          {checkingIdle ? (
            'Checking whether your session has ended.'
          ) : (
            <>
              Your session ends in {minutes} {minutes === 1 ? 'minute' : 'minutes'} without
              activity.
            </>
          )}
        </p>
        <p>
          Stay signed in to continue. Unsaved work and in-memory drafts will be lost when you sign
          out.
        </p>
      </div>
      {error === null ? null : (
        <div className="mt-3">
          <Alert tone="error">{error} Your session has not been extended.</Alert>
        </div>
      )}
      {waiting && error !== null ? (
        <p className="mt-2 text-sm text-muted">You can try again shortly.</p>
      ) : null}
      <div className="mt-5 flex flex-wrap justify-end gap-2">
        <Button
          variant="secondary"
          onClick={() => {
            void useAuthStore.getState().logout();
          }}
        >
          Sign out
        </Button>
        <Button
          ref={stay}
          busy={busy}
          busyLabel="Confirming activity…"
          disabled={waiting}
          onClick={() => {
            void useAuthStore.getState().reportActivity();
          }}
        >
          Stay signed in
        </Button>
      </div>
    </dialog>,
    document.body,
  );
}
