import type { ButtonHTMLAttributes } from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  /** Disables the button and marks it busy while an async action runs. */
  busy?: boolean;
}

const base =
  'inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium ' +
  'transition-colors disabled:cursor-not-allowed disabled:opacity-50';

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
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`${base} ${variants[variant]} ${className}`}
      disabled={disabled || busy}
      aria-busy={busy}
      {...rest}
    >
      {children}
    </button>
  );
}
