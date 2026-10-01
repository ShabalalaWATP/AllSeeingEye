import type { ButtonHTMLAttributes } from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  /**
   * Marks the button busy while an async action runs. A busy button stays
   * focusable (so keyboard focus is not lost) but ignores activation, which
   * also stops a busy submit button submitting its form again.
   */
  busy?: boolean;
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

export function Button({
  variant = 'primary',
  busy = false,
  className = '',
  type = 'button',
  disabled = false,
  onClick,
  children,
  ...rest
}: ButtonProps) {
  return (
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
      {children}
    </button>
  );
}
