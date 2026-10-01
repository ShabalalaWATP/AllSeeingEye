import type { ButtonHTMLAttributes, ReactNode, Ref } from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  /**
   * Marks the button busy while an async action runs. A busy button stays
   * focusable (so keyboard focus is not lost) but ignores activation, which
   * also stops a busy submit button submitting its form again. It always shows
   * a progress indicator beside its label.
   */
  busy?: boolean;
  /**
   * Visible progress text while busy, such as "Preparing PDF…". The button keeps its
   * accessible name, and the text is announced once through a polite live region.
   */
  busyLabel?: string | undefined;
  ref?: Ref<HTMLButtonElement> | undefined;
}

const base =
  'inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium ' +
  'transition-colors disabled:cursor-not-allowed disabled:opacity-50 ' +
  'aria-disabled:cursor-not-allowed aria-disabled:opacity-50';

const variants: Record<ButtonVariant, string> = {
  primary: 'bg-ember text-ground hover:bg-ember/90',
  secondary: 'border border-line bg-surface-2 text-text hover:bg-line',
  ghost: 'text-muted hover:bg-surface-2 hover:text-text',
  danger: 'border border-critical/50 text-critical hover:bg-critical/10',
};

/** A small ring that stays visible, without spinning, when motion is reduced. */
export function BusyIndicator() {
  return (
    <span
      aria-hidden="true"
      data-busy-indicator=""
      className="inline-block size-3.5 shrink-0 animate-spin rounded-full border-2 border-current border-t-transparent motion-reduce:animate-none"
    />
  );
}

function label(children: ReactNode, busy: boolean, busyLabel: string | undefined): ReactNode {
  if (!busy || busyLabel === undefined) return children;
  return (
    <>
      <span className="sr-only">{children}</span>
      <span aria-hidden="true">{busyLabel}</span>
    </>
  );
}

export function Button({
  variant = 'primary',
  busy = false,
  busyLabel,
  className = '',
  type = 'button',
  disabled = false,
  onClick,
  children,
  ...rest
}: ButtonProps) {
  const button = (
    <button
      type={type}
      className={`${base} ${variants[variant]} ${className}`}
      disabled={disabled}
      aria-disabled={busy ? true : undefined}
      aria-busy={busy}
      {...rest}
      onClick={(event) => {
        if (busy) {
          // Cancelling the click also cancels the form submission it would trigger.
          event.preventDefault();
          return;
        }
        onClick?.(event);
      }}
    >
      {busy ? <BusyIndicator /> : null}
      {label(children, busy, busyLabel)}
    </button>
  );
  if (busyLabel === undefined) return button;
  return (
    <>
      {button}
      {/* Present before it is filled, so screen readers announce the change. */}
      <span role="status" className="sr-only">
        {busy ? busyLabel : ''}
      </span>
    </>
  );
}
