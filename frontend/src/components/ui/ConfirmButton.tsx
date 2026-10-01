import { useState, type ReactNode } from 'react';

import { Button, type ButtonVariant } from './Button';
import { ConfirmDialog } from './ConfirmDialog';

export interface ConfirmButtonProps {
  /** The trigger's text. */
  label: ReactNode;
  variant?: ButtonVariant | undefined;
  className?: string | undefined;
  disabled?: boolean | undefined;
  /** True while the confirmed request runs; owned by the caller's action. */
  busy: boolean;
  title: string;
  confirmLabel: string;
  busyLabel: string;
  tone?: 'danger' | 'primary' | undefined;
  /** What will be affected and whether it can be undone. */
  children: ReactNode;
  onConfirm: () => void;
}

/**
 * A trigger and the shared confirmation for callers whose action reports its own outcome
 * (a page notice or form error). The dialog stays open while the request runs and closes
 * once it settles, so the caller's success or failure message is what the reader sees next.
 */
export function ConfirmButton({
  label,
  variant = 'danger',
  className,
  disabled = false,
  busy,
  title,
  confirmLabel,
  busyLabel,
  tone,
  children,
  onConfirm,
}: ConfirmButtonProps) {
  const [confirming, setConfirming] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [wasBusy, setWasBusy] = useState(busy);
  if (busy !== wasBusy) {
    // Adjusting state while rendering: close once a submitted request has settled.
    setWasBusy(busy);
    if (!busy && submitted) {
      setSubmitted(false);
      setConfirming(false);
    }
  }
  return (
    <>
      <Button
        variant={variant}
        className={className}
        disabled={disabled || busy}
        aria-haspopup="dialog"
        onClick={() => {
          setConfirming(true);
        }}
      >
        {label}
      </Button>
      <ConfirmDialog
        open={confirming}
        title={title}
        confirmLabel={confirmLabel}
        busyLabel={busyLabel}
        tone={tone}
        busy={busy}
        error={null}
        onCancel={() => {
          setConfirming(false);
        }}
        onConfirm={() => {
          setSubmitted(true);
          onConfirm();
        }}
      >
        {children}
      </ConfirmDialog>
    </>
  );
}
