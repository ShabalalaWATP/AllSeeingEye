import type { ReactNode } from 'react';

export type AlertTone = 'info' | 'success' | 'warning' | 'error';

const tones: Record<AlertTone, string> = {
  info: 'border-cyan/40 bg-cyan/10 text-text',
  success: 'border-good/40 bg-good/10 text-text',
  warning: 'border-amber/40 bg-amber/10 text-text',
  error: 'border-critical/40 bg-critical/10 text-text',
};

export interface AlertProps {
  tone?: AlertTone | undefined;
  title?: string | undefined;
  children: ReactNode;
  className?: string | undefined;
}

/** Inline notice. Errors use role="alert" so they are announced immediately. */
export function Alert({ tone = 'info', title, children, className = '' }: AlertProps) {
  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      className={`rounded-md border px-3 py-2 text-sm ${tones[tone]} ${className}`}
    >
      {title === undefined ? null : <p className="font-semibold">{title}</p>}
      <div>{children}</div>
    </div>
  );
}

export function LoadingNote({ label = 'Loading' }: { label?: string }) {
  return (
    <p role="status" className="text-sm text-muted">
      {label}
    </p>
  );
}
