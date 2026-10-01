import { useEffect, useId, useRef, type ReactNode, type RefObject } from 'react';
import { createPortal } from 'react-dom';

import { Alert } from './Alert';
import { Button } from './Button';

export interface ConfirmDialogProps {
  open: boolean;
  /** The question, naming the object, e.g. "Delete report “Kyiv grid”?". It names the dialog. */
  title: string;
  /** What will be affected and whether it can be undone. It describes the dialog. */
  children: ReactNode;
  confirmLabel: string;
  /** Progress text on the confirming control while the request runs. */
  busyLabel: string;
  cancelLabel?: string | undefined;
  tone?: 'danger' | 'primary' | undefined;
  busy: boolean;
  /** A failure from the last attempt. The dialog stays open so the reader can retry or cancel. */
  error: string | null;
  onConfirm: () => void;
  onCancel: () => void;
  /** Where focus goes on close when the control that opened the dialog no longer exists. */
  returnFocus?: RefObject<HTMLElement | null> | undefined;
}

/**
 * The shared confirmation for consequential actions. Native modal semantics keep focus
 * inside and the page inert. Cancel takes initial focus, so the consequential control is
 * never the default; Escape and Cancel only close. While the request runs the dialog
 * cannot be dismissed and the confirming control ignores repeats. A failure stays inside
 * the dialog beside a retry. Focus returns to the opener, or to `returnFocus` if it has gone.
 */
export function ConfirmDialog(props: ConfirmDialogProps) {
  return props.open ? <OpenConfirmDialog {...props} /> : null;
}

function focusTarget(target: HTMLElement): void {
  if (target.tabIndex < 0 && !target.hasAttribute('tabindex')) {
    // A heading is not a control, so programmatic focus needs no visible ring.
    target.tabIndex = -1;
    target.classList.add('focus:outline-none');
  }
  target.focus();
}

function OpenConfirmDialog({
  title,
  children,
  confirmLabel,
  busyLabel,
  cancelLabel = 'Cancel',
  tone = 'danger',
  busy,
  error,
  onConfirm,
  onCancel,
  returnFocus,
}: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const titleId = useId();
  const bodyId = useId();
  // The native listeners outlive renders, so they read the latest props through a ref.
  const latest = useRef({ busy, onCancel, returnFocus });
  useEffect(() => {
    latest.current = { busy, onCancel, returnFocus };
  });

  useEffect(() => {
    const opener = document.activeElement;
    // Without an explicit fallback, the heading of the section that held the opener.
    const region =
      opener instanceof HTMLElement ? opener.closest<HTMLElement>('section, main') : null;
    const dialog = dialogRef.current;
    if (!dialog) return;
    const keys = (event: KeyboardEvent) => {
      // Page shortcuts and other overlays' focus traps must not see keys meant for this dialog.
      event.stopPropagation();
      if (event.key !== 'Escape') return;
      event.preventDefault();
      if (!latest.current.busy) latest.current.onCancel();
    };
    dialog.addEventListener('keydown', keys);
    dialog.showModal();
    cancelRef.current?.focus();
    return () => {
      dialog.removeEventListener('keydown', keys);
      dialog.close();
      const explicit = latest.current.returnFocus?.current;
      // Let the native close settle before restoring focus explicitly.
      queueMicrotask(() => {
        if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
        if (document.activeElement === opener && opener !== document.body) return;
        const nearby = region?.isConnected
          ? (region.querySelector<HTMLElement>('h1, h2, h3') ?? region)
          : null;
        const fallback = explicit?.isConnected ? explicit : nearby;
        if (fallback) focusTarget(fallback);
      });
    };
  }, []);

  return createPortal(
    <dialog
      ref={dialogRef}
      role="alertdialog"
      aria-labelledby={titleId}
      aria-describedby={bodyId}
      className="m-auto w-[min(32rem,calc(100vw-2rem))] rounded-card border border-line bg-surface p-0 text-text shadow-card backdrop:bg-black/65"
      onCancel={(event) => {
        // Other close requests, such as a mobile back gesture, behave like Cancel.
        event.preventDefault();
        if (!busy) onCancel();
      }}
    >
      <div className="flex flex-col gap-4 p-5">
        <h2 id={titleId} className="text-base font-semibold">
          {title}
        </h2>
        <div id={bodyId} className="space-y-2 text-sm leading-6 text-muted">
          {children}
        </div>
        {error === null ? null : <Alert tone="error">{error}</Alert>}
        <div className="flex flex-wrap justify-end gap-2">
          <Button ref={cancelRef} variant="secondary" disabled={busy} onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button
            variant={tone === 'danger' ? 'danger' : 'primary'}
            busy={busy}
            busyLabel={busyLabel}
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </dialog>,
    document.body,
  );
}
